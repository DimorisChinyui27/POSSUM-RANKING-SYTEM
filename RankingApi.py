from flask import Flask, request, jsonify
from trueskill import TrueSkill

app = Flask(__name__)
#Env is a TrueSkill environment variable that creates a ranking environment where the probability of a draw is 0
env= TrueSkill(draw_probability=0.0)

#Creates a rating object using env global variable   
def Create_Rating(Nmu=25.0,Nsigma=8.333333333333334):
    return env.create_rating(mu=Nmu,sigma=Nsigma)

#Changes user ranking once that user gets a crown or losses a crown
@app.route("/updateuserrating", methods=['POST'])
def UpdateUserRating():
    request_data = request.get_json()
    Player_id = request_data["PlayerUserID"]
    win_status= bool(request_data["Win_status"])
    All_Users_Ratings_Data=list(request_data["AllUsersTopicData"])
    Player_rating_obj=None
    Player_rating_replacement_obj=None
    Competitors_list=[]
    New_Ratings_Data=[]
    for statdict in All_Users_Ratings_Data:
        if Player_id==statdict['UserID']:
            #Creates rating objects for the user who got crown from that user ratings data in database
            Player_rating_obj=Create_Rating(Nmu=float(statdict['Rating']),Nsigma=float(statdict['Confidence_Score']))
            Player_rating_replacement_obj=Player_rating_obj
        else:
            #Creates rating objects for other users from those users ratings data in database
            rating_obj= Create_Rating(Nmu=float(statdict['Rating']),Nsigma=float(statdict['Confidence_Score']))
            Competitors_list.append({statdict['UserID']:rating_obj})

    #Updates the Players ranking and every other users ranking
    for i in range(len(Competitors_list)):
        for key in Competitors_list[i]:
            if win_status:
                if i==0:
                    #Updates the Players ranking and last user ranking
                    Player_rating_obj,Competitors_list[i][key]= env.rate_1vs1(Player_rating_obj,Competitors_list[i][key])
                else:
                    #Updates all other users ranking when compared to winner
                    _, Competitors_list[i][key]= env.rate_1vs1(Player_rating_replacement_obj,Competitors_list[i][key])
            else:
                if i==0:
                    #Updates the winners ranking and 1 other users ranking
                    Competitors_list[i][key],Player_rating_obj= env.rate_1vs1(Competitors_list[i][key],Player_rating_obj)
                else:
                     #Updates all other users ranking when compared to winner
                     Competitors_list[i][key],_= env.rate_1vs1(Competitors_list[i][key],Player_rating_replacement_obj)
            New_Ratings_Data.append({"UserID":key,"Rating":Competitors_list[i][key].mu,"Confidence_Score":Competitors_list[i][key].sigma})

    New_Ratings_Data.append({"UserID":Player_id,"Rating":Player_rating_obj.mu,"Confidence_Score":Player_rating_obj.sigma})
    return jsonify(New_Ratings_Data)


@app.route("/getexpertsintopic", methods=['POST'])
def Get_Experts_in_Topic():
        request_data = request.get_json()
        Competitors_list=[]
        Search_top_expert_list=[]
        Top_Experts_List=[]
        top_expert=None
        All_Users_Ratings_Data = list(request_data["AllUsersTopicData"])
        for statdict in All_Users_Ratings_Data:
            rating_obj= Create_Rating(Nmu=float(statdict['Rating']),Nsigma=float(statdict['Confidence_Score']))
            Competitors_list.append({statdict['UserID']:rating_obj})
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

if __name__== "__main__":
    app.run()


