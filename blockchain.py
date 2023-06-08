import hashlib
import json
import time
from flask import Flask, jsonify, request, redirect, render_template, session
import uuid


app = Flask(__name__)
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'

class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        self.new_block(previous_hash='1', proof=100)

    def new_block(self, proof, previous_hash=None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        self.current_transactions = []
        self.chain.append(block)
        return block
    
    def get_transaction_ids(self, sender):
        transaction_ids = []
        for block in self.chain:
            for transaction in block['transactions']:
                if transaction['sender'] == sender:
                    transaction_ids.append(transaction['transactionID'])
        return transaction_ids

    def new_transaction(self, sender, report, transactionID):
        self.current_transactions.append({
            'sender': sender,
            'report': report,
            'transactionID': transactionID,
        })

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


blockchain = Blockchain()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)
    response = {
        'index': block['index'],
        'timestamp': block['timestamp'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }

    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    required_fields = ['sender', 'report', 'transactionID']
    if not all(field in values for field in required_fields):
        return 'Missing fields', 400

    index = blockchain.new_transaction(values['sender'], values['report'], values['transactionID'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/patient_register', methods=['GET', 'POST'])
def patient_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_data = {
            'username': username,
            'password': password
        }

        with open('users.json', 'a') as file:
            file.write(json.dumps(user_data) + '\n')

        return redirect('/patient_login')
    else:
        return render_template('patient_register.html')


@app.route('/patient_login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with open('users.json', 'r') as file:
            for line in file:
                user_data = json.loads(line)
                if user_data['username'] == username and user_data['password'] == password:
                    session['username'] = username
                    return redirect('/patient_dashboard')

        return 'Invalid credentials'
    else:
        return render_template('patient_login.html')
    

@app.route('/hospital_register', methods=['GET', 'POST'])
def hospital_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_data = {
            'username': username,
            'password': password
        }

        with open('users.json', 'a') as file:
            file.write(json.dumps(user_data) + '\n')

        return redirect('/hospital_login')
    else:
        return render_template('hospital_register.html')


@app.route('/hospital_login', methods=['GET', 'POST'])
def hospital_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with open('users.json', 'r') as file:
            for line in file:
                user_data = json.loads(line)
                if user_data['username'] == username and user_data['password'] == password:
                    session['username'] = username
                    return redirect('/hospital_dashboard')

        return 'Invalid credentials'
    else:
        return render_template('hospital_login.html')


@app.route('/patient_dashboard')
def patient_dashboard():
    if 'username' not in session:
        return redirect('/patient_login')

    transaction_ids = []

    with open('blockchain.json', 'r') as file:
        blockchain_data = json.load(file)
        for block in blockchain_data:
            for transaction in block['transactions']:
                if transaction['sender'] == session['username']:
                    transaction_ids.append(transaction['transactionID'])
    return render_template('patient_dashboard.html', transaction_ids=transaction_ids)

@app.route('/hospital_dashboard')
def hospital_dashboard():
    if 'username' not in session:
        return redirect('/hospital_login')

    transaction_ids = []

    with open('blockchain.json', 'r') as file:
        blockchain_data = json.load(file)
        for block in blockchain_data:
            for transaction in block['transactions']:
                if transaction['sender'] == session['username']:
                    transaction_ids.append(transaction['transactionID'])
    return render_template('hospital_dashboard.html', transaction_ids=transaction_ids)


@app.route('/push_report', methods=['GET', 'POST'])
def push_report():
    if request.method == 'POST':
        if 'username' not in session:
            return redirect('/login')

        username = session['username']
        report = request.form['report']

        transaction_id = str(uuid.uuid1())

        blockchain.new_transaction(
            sender=username,
            report=report,
            transactionID=transaction_id
        )
        mine()
        with open('blockchain.json', 'w') as file:
            file.write(json.dumps(blockchain.chain)+'\n')

        return redirect('/patient_dashboard')
    else:
        return render_template('push_report.html')


@app.route('/access_report', methods=['GET', 'POST'])
def access_report():
    if request.method == 'POST':
        if 'username' not in session:
            return redirect('/login')

        transaction_id = request.form['transaction_id']

        report = None
        with open('blockchain.json', 'r') as file:
            blockchain_data = json.load(file)
            for block in blockchain_data:
                for transaction in block['transactions']:
                    if transaction['transactionID'] == transaction_id:
                        report = transaction['report']
                        break

        if report:
            return f'Report: {report}'
        else:
            return 'Report not found'
    else:
        return render_template('access_report.html')

if __name__ == '__main__':
    app.run(debug=True)
