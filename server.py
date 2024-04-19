from flask import Flask, make_response, render_template, request, session, redirect, url_for, jsonify
from flask_mysqldb import MySQL
import pandas as pd

app = Flask(__name__)
app.secret_key = "04/13/2024"

app.config["MYSQL_UNIX_SOCKET"] = "/Applications/XAMPP/xamppfiles/var/mysql/mysql.sock"
# look in the XAMPP config file and see if the mysql.sock file has the address /temp/mysql.sock
# if not, you have to modify it
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_DB"] = "Usrs"
app.config["MYSQL_PASSWORD"] = ""

mysql = MySQL(app)

viewer = {
    "Alias": "*",
    "Criminals": ["FirstName", 'LastName', 'V_status', 'P_status'],
    'Crimes': '*',
    'Sentences': '*',
    'Prob_officers': ['FirstName', 'LastName', 'Status'],
    'Crime_charges': "*", 
    'Crime_officers': "*",
    'Officers': ['FirstName', 'LastName', 'Precinct', 'Badge', 'Status'], 
    'Appeals': "*",
    'Crime_codes': '*'
}

employee = {
    "Alias": "*",
    "Criminals": "*",
    'Crimes': "*",
    'Sentences': "*",
    'Prob_officers': "*",
    'Crime_charges': "*", 
    'Crime_officers': "*",
    'Officers': "*", 
    'Appeals': "*",
    'Crime_codes': "*"
}

'''
viewer previleges: 
GRANT SELECT ON Alias TO viewer;
GRANT SELECT (Criminal_ID, FirstName, LastName, V_status, P_status) ON Criminals TO viewer;
GRANT SELECT ON Crimes TO viewer;
GRANT SELECT ON Sentences TO viewer;
GRANT SELECT (Prob_ID, FirstName, LastName, Status) ON Prob_officers TO viewer;
GRANT SELECT ON Crime_charges TO viewer;
GRANT SELECT ON Crime_officers TO viewer;
GRANT SELECT (Officer_ID, FirstName, LastName, Precinct, Badge, Status) ON Officers TO viewer;
GRANT SELECT ON Appeals TO viewer;
GRANT SELECT ON Crime_codes TO viewer;

employee previleges:
GRANT SELECT ON Alias TO employee;
GRANT SELECT ON Criminals TO employee;
GRANT SELECT ON Crimes TO employee;
GRANT SELECT ON Sentences TO employee;
GRANT SELECT ON Prob_officers TO employee;
GRANT SELECT ON Crime_charges TO employee;
GRANT SELECT ON Crime_officers TO employee;
GRANT SELECT ON Officers TO employee;
GRANT SELECT ON Appeals TO employee;
GRANT SELECT ON Crime_codes TO employee;
'''

def runstatement(statement, commit=False):
    cursor = mysql.connection.cursor()
    cursor.execute(statement)
    results = cursor.fetchall()
    if commit:
        mysql.connection.commit()
    df = ""
    if cursor.description:
        column_names = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(results, columns = column_names)
    cursor.close()
    return df

def generateStatementViewer(table, action, query, attr="*"):
    if isinstance(attr, list):
        attr = ", ".join(attr)
    if action.lower() != "select":
        return pd.DataFrame()
    sql = f"{action.upper()} {attr.upper()} FROM {table.upper()}"
    if query:
        sql += f" WHERE {query}"
    return sql

@app.route('/', methods=['GET', 'POST'])
def login():
    error_message = None
    logout_message = None
    if 'username' in session:
        return redirect(url_for('profile', username=session['username']))
    if request.method == 'POST':
        if 'login' in request.form:
            username = request.form['uname']
            password = request.form['pwd']
            df = runstatement(f'''call checkUsr('{username}', '{password}')''')
            if df.iloc[0, 0] != 0:
                session["username"] = username
                session["firstName"] = df.iloc[0, 2]
                session["lastName"] = df.iloc[0, 3]
                session["permission"] = df.iloc[0, 4]

                return redirect(url_for('profile', username=username))
            else:
                error_message = "Invalid username or password. Please try again."
    # Check if logout message exists in the session
    if 'logout_message' in session:
        logout_message = session.pop('logout_message')
    
    return render_template("login.html", error_message=error_message, logout_message=logout_message)

@app.route("/<username>/profile")
def profile(username):
    return render_template("profile.html", 
                    username=username, 
                    firstname=session.get("firstName"), 
                    lastname=session.get("lastName"))

@app.route('/logout')
def logout():
    session.clear()
    session['logout_message'] = "You have been logged out successfully!"
    return redirect(url_for('login'))

@app.route("/registration", methods=['GET', 'POST'])
def registration():
    error_message = None  # Initialize error message variable
    if 'username' in session:
        return redirect(url_for('profile', username=session['username']))
    if request.method == 'POST':
        if 'submit' in request.form:
            df = runstatement(f'''call checkRegister('{request.form['uname']}')''')
            # if uname not unique, returns firstname, lastname
            if len(df) == 0:
                session["firstName"] = request.form['fname']
                session["lastName"] = request.form['lname']
                session["username"] = request.form['uname']
                session["password"] = request.form['pwd']
                runstatement("use Usrs", commit= True)
                runstatement(f"""INSERT INTO Usrs (usr_ID, usr_PW, firstName, lastName) VALUES 
                            ('{session["username"]}', '{session["password"]}', 
                            '{session["firstName"]}', '{session["lastName"]}')""", commit=True)
                return redirect(url_for('login', username=session["username"]))
            else:
                error_message = f"Username '{request.form['uname']}' already exists. Please choose a different username."  # Set error message
    return render_template("registration.html", error_message=error_message)

@app.route("/<username>/alias",methods=['GET', 'POST'])
def alias(username):
    runstatement('''use Criminal_Records''', commit=True)
    if request.method == 'POST' and session.get("permission") == 'host':
        alias_id = request.form.getlist('alias_id[]')
        alias = request.form.getlist('alias[]')
        criminal_id = request.form.getlist('criminal_id[]')
        sql = f'''INSERT INTO Alias (Alias_ID, Alias, Criminal_ID) VALUES '''
        for ind in range(len(alias_id)):
            if ind == len(alias_id) - 1:
                sql += f"({alias_id[ind]}, '{alias[ind]}', {criminal_id[ind]});"
            else:
                sql += f"({alias_id[ind]}, '{alias[ind]}', {criminal_id[ind]}),"
        try:
            print(sql)
            runstatement(sql, commit=True)
            runstatement('''use Criminal_Records''', commit=True)
            alias_id = request.args.get('alias_id')
            criminal_id = request.args.get('criminal_id')
            alias = request.args.get('alias')
            query = ""

            if alias_id:
                query += f"Alias_ID = '{alias_id}'"
            if criminal_id:
                if query:
                    query += " AND "
                query += f"Criminal_ID = '{criminal_id}'"
            if alias:
                if query:
                    query += " AND "
                query += f"Alias = '{alias}'"

            if session["permission"] == "viewer":
                table = viewer['Alias']
            else:
                table = employee['Alias']

            sql = generateStatementViewer('Alias', 'select', query, table)
            df = runstatement(sql)
            return df.to_html(classes="styled-table", index=False)
        except:
            return make_response("Error: Alias ID already exists or required data is missing.", 400)
    else:
        query = None
        displayMode = 'inline-block'

        if session["permission"] == "viewer":
            table = viewer['Alias']
        else:
            table = employee['Alias']

        sql = generateStatementViewer('Alias', 'select', query, table)
        permission = session.get("permission")
        df = runstatement(sql)
        return render_template("alias.html", data=df.to_html(classes="styled-table", index=False), displayMode=displayMode,permission=permission)

@app.route("/<username>/alias/filter", methods=['GET'])
def filter_alias(username):
    runstatement('''use Criminal_Records''', commit=True)
    if request.method == 'POST' and session.get("permission") == 'host':
        alias_id = request.form.getlist('alias_id[]')
        alias = request.form.getlist('alias[]')
        criminal_id = request.form.getlist('criminal_id[]')
        sql = f'''INSERT INTO Alias (Alias_ID, Alias, Criminal_ID) VALUES '''
        for ind in range(len(alias_id)):
            if ind == len(alias_id) - 1:
                sql += f"({alias_id[ind]}, '{alias[ind]}', {criminal_id[ind]});"
            else:
                sql += f"({alias_id[ind]}, '{alias[ind]}', {criminal_id[ind]}),"
        try:
            print(sql)
            runstatement(sql, commit=True)
            runstatement('''use Criminal_Records''', commit=True)
            alias_id = request.args.get('alias_id')
            criminal_id = request.args.get('criminal_id')
            alias = request.args.get('alias')
            query = ""

            if alias_id:
                query += f"Alias_ID = '{alias_id}'"
            if criminal_id:
                if query:
                    query += " AND "
                query += f"Criminal_ID = '{criminal_id}'"
            if alias:
                if query:
                    query += " AND "
                query += f"Alias = '{alias}'"

            if session["permission"] == "viewer":
                table = viewer['Alias']
            else:
                table = employee['Alias']

            sql = generateStatementViewer('Alias', 'select', query, table)
            df = runstatement(sql)
            return df.to_html(classes="styled-table", index=False)
        except:
            return make_response("Error: Alias ID already exists or required data is missing.", 400)
    else:
        runstatement('''use Criminal_Records''', commit=True)
        alias_id = request.args.get('alias_id')
        criminal_id = request.args.get('criminal_id')
        alias = request.args.get('alias')
        query = ""

        if alias_id:
            query += f"Alias_ID = '{alias_id}'"
        if criminal_id:
            if query:
                query += " AND "
            query += f"Criminal_ID = '{criminal_id}'"
        if alias:
            if query:
                query += " AND "
            query += f"Alias = '{alias}'"

        if session["permission"] == "viewer":
            table = viewer['Alias']
        else:
            table = employee['Alias']

        sql = generateStatementViewer('Alias', 'select', query, table)
        df = runstatement(sql)
        return df.to_html(classes="styled-table", index=False)

@app.route("/<username>/appeals")
def appeals(username):
    runstatement('''use Criminal_Records''', commit=True)
    appeal_id = request.args.get('appeal_id')
    displayMode = 'none'
    if appeal_id:
        query = f"Appeal_ID = '{appeal_id}'"
        displayMode = 'inline-block'
    else:
        query = None

    if session["permission"] == "viewer":
        table = viewer['Appeals']
    elif session["permission"] == "employee" or "host":
        table = employee['Appeals']
        
    sql = generateStatementViewer('Appeals', 'select', query, table)
    df = runstatement(sql)
    return render_template("appeals.html", data=df.to_html(classes="styled-table", index=False),displayMode=displayMode)

@app.route("/<username>/crime_charges")
def crime_charges(username):
    runstatement('''use Criminal_Records''', commit=True)
    displayMode = 'none'
    charge_id = request.args.get('charge_id')
    if charge_id:
        query = f"Charge_ID = '{charge_id}'"
        displayMode = 'inline-block'
    else:
        query = None

    if session["permission"] == "viewer":
        table = viewer['Crime_charges']
    elif session["permission"] == "employee" or "host":
        table = employee['Crime_charges']

    sql = generateStatementViewer('Crime_charges', 'select', query, table)
    df = runstatement(sql)
    return render_template("crime_charges.html", data=df.to_html(classes="styled-table", index=False),displayMode=displayMode)

@app.route("/<username>/crime_codes")
def crime_codes(username):
    runstatement('''use Criminal_Records''', commit=True)
    crime_code = request.args.get('crime_code')
    displayMode = 'none'
    if crime_code:
        query = f"Crime_code = '{crime_code}'"
        displayMode = 'inline-block'
    else:
        query = None

    if session["permission"] == "viewer":
        table = viewer['Crime_codes']
    elif session["permission"] == "employee" or "host":
        table = employee['Crime_codes']
        
    sql = generateStatementViewer('Crime_codes', 'select', query, table)
    df = runstatement(sql)
    return render_template("crime_codes.html", data=df.to_html(classes="styled-table", index=False),displayMode=displayMode)

@app.route("/<username>/crime_officers")
def crime_officers(username):
    runstatement('''use Criminal_Records''', commit=True)
    crime_id = request.args.get('crime_id')
    displayMode = 'none'
    if crime_id:
        query = f"Crime_ID = '{crime_id}'"
        displayMode = 'inline-block'
    else:
        query = None

    if session["permission"] == "viewer":
        table = viewer['Crime_officers']
    elif session["permission"] == "employee" or "host":
        table = employee['Crime_officers']


    sql = generateStatementViewer('Crime_officers', 'select', query, table)
    df = runstatement(sql)
    return render_template("crime_officers.html", data=df.to_html(classes="styled-table", index=False),displayMode=displayMode)

@app.route("/<username>/crimes")
def crimes(username):
    runstatement('''use Criminal_Records''', commit=True)
    crime_id = request.args.get('crime_id')
    displayMode = 'none'
    if crime_id:
        displayMode = 'inline-block'
        query = f"Crime_ID = '{crime_id}'"
    else:
        query = None

    if session["permission"] == "viewer":
        table = viewer['Crimes']
    elif session["permission"] == "employee" or "host":
        table = employee['Crimes']

    sql = generateStatementViewer('Crimes', 'select', query, table)
    df = runstatement(sql)
    return render_template("crimes.html", data=df.to_html(classes="styled-table", index=False),displayMode=displayMode)

@app.route("/<username>/criminals")
def criminals(username):
    runstatement('''use Criminal_Records''', commit=True)
    show = 'none'
    criminal_id = request.args.get('criminal_id')
    fname = request.args.get('FirstName')
    lname = request.args.get('LastName')
    query = None

    if criminal_id:
        show = 'inline-block'
        query = f"Criminal_ID = '{criminal_id}'"
    elif fname and lname:
        show = 'inline-block'
        query = f"FirstName = '{fname}' AND LastName = '{lname}'"
    else:
        query = None

    if session["permission"] == "viewer":
        table = viewer['Criminals']
    elif session["permission"] == "employee" or "host":
        table = employee['Criminals']

    sql = generateStatementViewer('Criminals', 'select', query, table)
    df = runstatement(sql)
    return render_template("criminals.html", data=df.to_html(classes="styled-table", index=False), show=show)

@app.route("/<username>/prob_officers")
def prob_officers(username):
    runstatement('''use Criminal_Records''', commit=True)
    prob_id = request.args.get('prob_id')
    fname = request.args.get('FirstName')
    lname = request.args.get('LastName')
    display = 'none'
    query = None

    if prob_id:
        display = 'inline-block'
        query = f"Prob_ID = '{prob_id}'"
    elif fname and lname:
        display = 'inline-block'
        query = f"FirstName = '{fname}' AND LastName = '{lname}'"
    else:
        query = None

    if session["permission"] == "viewer":
        table = viewer['Prob_officers']
    elif session["permission"] == "employee" or "host":
        table = employee['Prob_officers']

    sql = generateStatementViewer('Prob_officers', 'select', query, table)
    df = runstatement(sql)
    return render_template("prob_officers.html", data=df.to_html(classes="styled-table", index=False), show=display)

@app.route("/<username>/officers")
def officers(username):
    runstatement('''use Criminal_Records''', commit=True)
    displayMode = 'none'
    officer_id = request.args.get('officer_id')
    fname = request.args.get('FirstName')
    lname = request.args.get('LastName')
    badge = request.args.get('Badage')
    
    query = None

    if officer_id:
        displayMode = 'inline-block'
        query = f"Officer_ID = '{officer_id}'"
    elif fname and lname:
        displayMode = 'inline-block'
        query = f"FirstName = '{fname}' AND LastName = '{lname}'"
    elif badge:
        displayMode = 'inline-block'
        query = f"Badge = '{badge}'"
    else:
        query = None

    if session["permission"] == "viewer":
        table = viewer['Officers']
    elif session["permission"] == "employee" or "host":
        table = employee['Officers']

    sql = generateStatementViewer('Officers', 'select', query, table)
    df = runstatement(sql)
    return render_template("officers.html", data=df.to_html(classes="styled-table", index=False),displayMode=displayMode)


@app.route("/<username>/sentences")
def sentences(username):
    runstatement('''use Criminal_Records''', commit=True)
    displayMode = 'none'
    sentence_id = request.args.get('sentence_id')
    if sentence_id:
        displayMode = 'inline-block'
        query = f"Sentence_ID = '{sentence_id}'"
    else:
        query = None

    if session["permission"] == "viewer":
        table = viewer['Sentences']
    elif session["permission"] == "employee" or "host":
        table = employee['Sentences']

    sql = generateStatementViewer('Sentences', 'select', query, table)
    df = runstatement(sql)
    return render_template("sentences.html", data=df.to_html(classes="styled-table", index=False),displayMode=displayMode)


if __name__ == "__main__":
    app.run(debug=True)