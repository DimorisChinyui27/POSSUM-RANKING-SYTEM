from flask import Flask, request, jsonify
import sqlite3
from trueskill import TrueSkill

app = Flask(__name__)
#Env is a TrueSkill environment variable that creates a ranking environment where the probability of a draw is 0
env= TrueSkill(draw_probability=0.0)

def db_connection():
    conn=None
    try:
        conn=sqlite3.connect('TopicsofInterest.sqlite')
    except sqlite3.Error as e:
        return e
    return conn

#Finds a  topic table exist in db
def Topic_Table_Exist(topic_name,cursor):
    try:
        sql="""SELECT EXISTS (SELECT name FROM sqlite_schema WHERE type='table' AND name=?)"""
        cursor.execute(sql,(topic_name,))
        return bool(cursor.fetchall()[0][0])
    except Exception as e:
        print(e)
 #Finds if a user making request exist in db   
def User_Exist(topic_name, username,cursor):
    try:
        sql="SELECT EXISTS (SELECT * FROM "+topic_name+ " WHERE Username=?)"
        cursor.execute(sql,(username,))
        return bool(cursor.fetchall()[0][0])
    except Exception as e:
        print(e)

 #Creates a rating object using env global variable   
def Create_Rating(Nmu=25.0,Nsigma=8.333333333333334):
    return env.create_rating(mu=Nmu,sigma=Nsigma)

#Creates a new topic and adds the user to that topic
@app.route("/createusertopic/<string:topic_name>", methods=['POST'])   
def Create_New_User_Topic(topic_name):
    username= request.form['Username']
    conn = db_connection()
    cursor = conn.cursor()
    #Creates a new player rank and sets it in new topic table
    New_player=Create_Rating()
    if Topic_Table_Exist(topic_name,cursor):
        return f"Topic on {topic_name} already exist try to add it instead"
    else:
        sql_query="CREATE TABLE "+topic_name+" ( id INTEGER PRIMARY KEY, Username TEXT NOT NULL, Rank REAL NOT NULL, Confidence_score REAL NOT NULL)"
        cursor.execute(sql_query)
        sql="INSERT INTO "+topic_name+" (Username,Rank,Confidence_score) VALUES (?,?,?)"
        cursor.execute(sql,(username,New_player.mu,New_player.sigma))
        conn.commit()
        return f"Topic named {topic_name} created and {username} successfully added",201

@app.route("/addusertotopic/<string:topic_name>", methods=['POST'])   
def Add_User_To_Topic(topic_name):
    username= request.form['Username']
    conn = db_connection()
    cursor = conn.cursor()
    #Creates a new player rank and adds it to already existing table
    New_player=Create_Rating()
    if Topic_Table_Exist(topic_name,cursor):
        if not User_Exist(topic_name, username,cursor): 
            sql="INSERT INTO "+topic_name+" (Username,Rank,Confidence_score) VALUES (?,?,?)"
            cursor.execute(sql,(username,New_player.mu,New_player.sigma))
            conn.commit()
            return f"{username} successfully added to {topic_name} table",201
        else:
            return f"{username} already exist in {topic_name} table"
    else:
        return f"{topic_name} table does not exist on database"

#Removes a player from a topic table when they remove that topic as topic of interest
@app.route("/removeuserfromtopic/<string:topic_name>", methods=['PUT'])
def Remove_User_From_Topic(topic_name):
    username= request.form['Username']
    conn = db_connection()
    cursor = conn.cursor()
    if Topic_Table_Exist(topic_name,cursor):
        if User_Exist(topic_name, username,cursor): 
            sql="DELETE FROM "+topic_name+" WHERE Username=?"
            cursor.execute(sql,(username,))
            conn.commit()
            return f"{username} successfully deleted from {topic_name} table",201
        else:
            return f"{username} does not exist on {topic_name} table"
    else:
        return f"{topic_name} table does not exist on database"

#Changes user ranking once that user gets a crown
@app.route("/updateuserrating/<string:topic_name>", methods=['PUT'])
def UpdateUserRating(topic_name):
    username= request.form['Username']
    conn = db_connection()
    cursor = conn.cursor()
    if Topic_Table_Exist(topic_name,cursor):
        if User_Exist(topic_name, username,cursor):
            user_rating_obj=None
            Competitors_list=[]
            cursor.execute("SELECT * FROM "+topic_name)
            All_Users_Ratings_Data = [
            dict( id=row[0], Username= row[1], Rank = row[2], Confidence_score=row[3])
            for row in cursor.fetchall()
            ]
            for statdict in All_Users_Ratings_Data:
                if username==statdict['Username']:
                    #Creates rating objects for the user who got crown from that user ratings data in database
                    user_rating_obj=Create_Rating(Nmu=float(statdict['Rank']),Nsigma=float(statdict['Confidence_score']))
                    
                else:
                    #Creates rating objects for other users from those users ratings data in database
                    rating_obj= Create_Rating(Nmu=float(statdict['Rank']),Nsigma=float(statdict['Confidence_score']))
                    Competitors_list.append({statdict['Username']:rating_obj})
            #Updates the winner ranking and every other users ranking
            for i in range(len(Competitors_list)):
                for key in Competitors_list[i]:
                    if i==0:
                        #Updates the winners ranking and 1 other users ranking
                        user_rating_obj,Competitors_list[i][key]= env.rate_1vs1(user_rating_obj,Competitors_list[i][key])
                    else:
                        #Updates all other users ranking when compared to winner
                        _, Competitors_list[i][key]= env.rate_1vs1(user_rating_obj,Competitors_list[i][key])

            Competitors_list.append({username:user_rating_obj})
            sql="UPDATE "+topic_name+" SET Rank=?, Confidence_score=? WHERE Username=?"
            #Saves new rankings to db
            for comp in Competitors_list:
                for key in comp:
                    cursor.execute(sql,(comp[key].mu,comp[key].sigma,key))
                    conn.commit()
            return f"{username} successfully updated in {topic_name} table",201

            
        else:
            return f"{username} does not exist on {topic_name} table"
    else:
        return f"{topic_name} table does not exist on database"

@app.route("/getexpertsintopic/<string:topic_name>", methods=['GET'])
def Get_Experts_in_Topic(topic_name):
    conn = db_connection()
    cursor = conn.cursor()
    if Topic_Table_Exist(topic_name,cursor):
        Competitors_list=[]
        Search_top_expert_list=[]
        Top_Experts_List=[]
        top_expert=None
        cursor.execute("SELECT * FROM "+topic_name)
        All_Users_Ratings_Data = [
            dict( id=row[0], Username= row[1], Rank = row[2], Confidence_score=row[3])
            for row in cursor.fetchall()
            ]
        for statdict in All_Users_Ratings_Data:
            rating_obj= Create_Rating(Nmu=float(statdict['Rank']),Nsigma=float(statdict['Confidence_score']))
            Competitors_list.append({statdict['Username']:rating_obj})
        #Searches for top ranking user
        for comp in Competitors_list:
            for key in comp:
                Search_top_expert_list.append(comp[key].mu)

        Search_top_expert_list.sort(reverse=True)

        for comp in Competitors_list:
            for key in comp:
                if comp[key].mu==Search_top_expert_list[0]:
                    top_expert=comp[key]
        #Compares top ranking user to others to get experts
        for comp in Competitors_list:
            for key in comp:
                #If probability of match quality==50% then other user also expert
                if env.quality_1vs1(top_expert,comp[key])>=0.50:
                    Top_Experts_List.append({key:comp[key].mu})
                else:
                    pass
        return jsonify(Top_Experts_List)
    else:
            return f"{topic_name} table does not exist on database"

if __name__== "__main__":
    app.run()

#For Mysql version just pip install pymsql,change everything written as "sqllite3" to "pymsql"
#And Anywhere you see "?" change to "%s"
