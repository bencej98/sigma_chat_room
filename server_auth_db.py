import sqlite3
import bcrypt

username = "username"
password = "password"

# This function return dictionaries instead of tuples from the sql queries
def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


# Establishes connection with the database
connection = sqlite3.connect("testDB.db")

# Have to assign dict_factory so that cursor iterates through the given dicts
connection.row_factory = dict_factory

# Creating the cursor to execute SQL statements and fetch results
cur = connection.cursor()

def user_db_creation():

    cur.execute(   """
                        SELECT *
                        FROM users
                        WHERE username = ?
                        """
                        , (username,))
    validator = cur.fetchone()
    if validator is not None:
        pass # Some kind of error handling

    # Stores the hased password and the username in a variable
    hashed_password = generate_password_hash(password)
    cur.execute(      """
                        INSERT INTO users (username, hash)
                        VALUES (?, ?)
                        """
                        , (username, hashed_password))

    connection.commit()

def user_login():

    #Query database for username (it gives back a cursor!)
    user_data = cur.execute( """
                                SELECT * 
                                FROM users
                                WHERE username = ?
                                """ 
                                , (username))
    user = user_data.fetchall()

    if not any(user):
        pass
    elif check_password_hash(user[0]["hash"], (password)) != True:
        print("Invalid username and/or password!")
        return "json msg"

