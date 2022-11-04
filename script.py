import os
import json
import discord
from discord.ext import commands

#Hier zwischen die Anführungszeichen den Token einfügen
TOKEN = ''

intents = discord.Intents.default()
intents.message_content = True

#Dictionary aller Studenten, diese Liste wird zum persistieren in eine JSON-Datei gespeichert
listOfStudents = {}

#Dictionary aller Abkürungen für Kanäle
abbreviationDict = {}


#Repräsnetiert Studenten durch CampusID, Anzahl der Korrekturen und den aktuellen Korrektur-Status
class Student:
    def __init__(self, campusId, numberOfCorrections = 0, isCorrected = False):
         self.campusId = campusId
         self.numberOfCorrections = numberOfCorrections
         self.isCorrected = isCorrected
         
    def __repr__(self):
        return "CampusId: " + str(self.campusId) + "\nnumberOfCorrections: " + str(self.numberOfCorrections) + "\nisCorrected: " + str(self.isCorrected)
         
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__)
 


#Lädt die Studenten-Liste beim starten des Bots aus einer JSON-Datei 
files = [f for f in os.listdir('.') if os.path.isfile(f)]
for f in files:
    if f.startswith("data-") and f.endswith(".json"):
        channelName = f[5:-5]
        listOfStudents[channelName] = []
        with open(f, 'r', encoding='utf-8') as f:
            try:
                channelList = json.loads(f.read())
                for element in channelList:
                    try:
                        student = Student(**json.loads(element))
                        listOfStudents[channelName].append(student)
                    except ValueError:
                        print('Decoding JSON has failed')
                print("Die Liste der Stundenten wurde geladen. \n")
            except ValueError:
                print('Error reading File')
    if f == "channelNameAbbreviation.json":
        with open("channelNameAbbreviation.json") as f:
            try:
                abbreviationDict = json.loads(f.read())
                print("Die Liste der Abkürzungen wurde geladen: \n" +str(abbreviationDict))
            except ValueError:
                print('Error reading File')


bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)


        
#Gibt Name, Anzahl der Korrekturen und Link aus Markdown-Datei zu dem nächsten zu bearbeitenden Studenten aus
@bot.command(brief="Gibt den nächsten zu bearbeitenden Stundenten aus", description="Gibt den nächsten zu bearbeitenden Stundenten aus, nur Staffs können diesen Befehl ausführen")
@commands.has_role("Staff")
async def next(ctx, arg):
    if arg not in abbreviationDict.keys():
        await ctx.send("Diese Kanal-Abkürzung ist nicht bekannt.")
    numberOfUncorrectedStudents = len(list(filter(lambda student: student.isCorrected == False, listOfStudents[abbreviationDict[arg]] )))
    if(numberOfUncorrectedStudents < 1):
        await ctx.send("Momentan ist nichts zu tun.")
    else:
        greeting = (" Noch "+ str(numberOfUncorrectedStudents - 1) + " übrig") if numberOfUncorrectedStudents > 1 else " Das ist der letzte :)"
        campusId = correctStudent(abbreviationDict[arg])
        await ctx.send("CampusID: "+ campusId + " | " + greeting)
        await ctx.send("Es war die: " + str(listOfStudents[abbreviationDict[arg]][getIndex(abbreviationDict[arg], campusId)].numberOfCorrections) +". Korrektur")
        await ctx.send(findLink(abbreviationDict[arg], campusId))
        saveChannel(abbreviationDict[arg])
            
@next.error
async def next_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("Nur Staffs können diesen Befehl ausführen.")

#Korrigiere Student, indem die Anzahl der Korrekturen erhöht und Status auf True geändert wird, außderdem wird die CampusID des Studenten zurückgegeben
def correctStudent(channelName):
    numOfCorrections = 0
    while(numOfCorrections < 50):
        for student in listOfStudents[channelName]:
            if student.isCorrected == False and student.numberOfCorrections == numOfCorrections:
                student.numberOfCorrections += 1
                student.isCorrected = True
                return student.campusId
        numOfCorrections += 1
        

#Gibt Links zu einer CampusID aus der Markdown-Datei wieder
def findLink(channelName, campusId):
    with open(f"{channelName}.md") as overview:
        for line in overview:
            if(line.split("|")[1] == campusId):
                return "Code Repo: " + line.split("|")[2] + "\nTest Repo: " + line.split("|")[3] + "\nTest Page: " + line.split("|")[4]
        return "Link not found"
    

#Löscht die lokale Liste der Studenten und leert die JSON Datei
@bot.command(brief="Löscht die Liste der Studenten", description="Löscht die Liste der Studenten, nur Staffs können diesen Befehl ausführen")
@commands.has_role("Staff")
async def clearlist(ctx, arg):
    if arg not in abbreviationDict.keys():
        await ctx.send("Diese Kanal-Abkürzung ist nicht bekannt.")
    listOfStudents[abbreviationDict[arg]].clear()
    saveChannel(abbreviationDict[arg])
    await ctx.send("Die Liste wurde geleert.")
            
@clearlist.error
async def clearlist_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("Nur Staffs können diesen Befehl ausführen.")
        
#Ändert die Abkürung eines Kanals welcher im "next" und "clearlist" Befehl genutzt wird
@bot.command(brief="Ändert die Abkürzung eines Kanals für next und clearlist", description="Ändert die Abkürung eines Kanals welcher im 'next' und 'clearlist' Befehl genutzt wird")
@commands.has_role("Staff")
async def nickname(ctx, arg):
    abbreviationDict[arg] = ctx.channel.name
    with open(f"channelNameAbbreviation.json", 'w', encoding='utf-8') as f:
        json.dump(abbreviationDict, f, indent=4)
    await ctx.send(f"Die Abkürzung dieses Kanals ist nun '{arg}'.")
    
            
@nickname.error
async def nickname_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("Nur Staffs können diesen Befehl ausführen.")

#Fügt einen Studenten in die Liste hinzu, wenn dieser neu ist. Ansonsten wird er auf "möchte korrigiert werden" gesetzt und ans Ende der Liste verschoben.
@bot.command(brief="Bitte \"!correct CampusID\" eingeben", description="Bitte \"!correct CampusID\" eingeben")
async def correct(ctx, arg):
    if ctx.channel.name not in listOfStudents.keys():
        listOfStudents[ctx.channel.name] = []
        
    if not isInList(ctx.channel.name, arg):
        listOfStudents[ctx.channel.name].append(Student(arg))
        saveChannel(ctx.channel.name)
    else:
        indexOfStudent = getIndex(ctx.channel.name, arg)
        if indexOfStudent > -1:
            student = listOfStudents[ctx.channel.name][indexOfStudent]
            listOfStudents[ctx.channel.name].remove(student)
            student.isCorrected = False
            listOfStudents[ctx.channel.name].append(student)
            saveChannel(ctx.channel.name)
    await ctx.send(arg + " du wurdest der Liste hinzugefügt.")

#Prüft ob CampusID in der Studenten-Liste enthalten ist 
def isInList(channelName, campusId):
    for student in listOfStudents[channelName]:
        if student.campusId == campusId:
            return True
    return False

#Gibt den Index eines Studenten in der Studneten-Liste über seine CampusID wieder
def getIndex(channelName, campusId):
    for student in listOfStudents[channelName]:
        if student.campusId == campusId:
            return listOfStudents[channelName].index(student)
    return -1


def saveChannel(channelName):
    with open(f"data-{channelName}.json", 'w', encoding='utf-8') as f:
        json.dump([student.toJSON() for student in listOfStudents[channelName]], f, indent=4)



bot.run(TOKEN)
