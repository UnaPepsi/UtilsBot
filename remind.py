import csv
import time
from discord import User
import requests

headers = {"Authorization":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3ODc4NTgyMjgyODI2NTUxNCIsImJvdCI6dHJ1ZSwiaWF0IjoxNzAzNzkzNDM0fQ.Z51Wy-UOn4r9CqzG8lhWEynSpSWS6mQ6tkZmLyNWI68"}

def add_remind(user: int,channel_id: int,reason: str,days: int=0,hours: int=0,minutes: int=0,is_dm="") -> str:
	user_voted = requests.get(f"https://top.gg/api/bots/778785822828265514/check?userId={user}",headers=headers).json()
	print(user_voted,user)
	try:
		user_voted = user_voted['voted']
	except KeyError:
		pass
	if len(reason) > 100 and user_voted != 1:
		return "Your reminder's reason is way too big, to have a bigger limit please consider giving me a vote on <https://top.gg/bot/778785822828265514/vote> :D"
	if len(reason) > 1500:
		return "You can't have a reminder with a reason with more than 1500 characters"
	timestamp = int(time.time())+(days*86400)+(hours*3600)+(minutes*60)
	id = 0
	if timestamp - time.time() > 31536000:
		return "You can't have a reminder with a time longer than a year"
	with open("tasks.csv","r") as f:
		reader = csv.reader(f,delimiter="-")
		for line in reader:
			if str(user) == line[0]:
				id += 1
				# return "You already have a reminder scheduled!"
	if id > 10 and user_voted != 1:
		return "You can only have a maximum of 10 reminders at once, you can have even more reminders if you give me a vote on <https://top.gg/bot/778785822828265514/vote> :D"
	if id > 100:
		return "You have reached the limit of reminders you can have at once :("
	with open("tasks.csv","a",newline="") as f:
		writer = csv.writer(f,delimiter="-")
		writer.writerow([user,timestamp,channel_id,reason,id,is_dm])
	return f'Reminder for <t:{timestamp}> of id `{id}` with reason: "{reason}" added successfully'

def remove_reminder(user: int,id: str) -> str:
	lines = []
	done = "You have no reminder with that id"
	with open("tasks.csv","r+",newline="") as f:
		reader = csv.reader(f,delimiter="-")
		for line in reader:
			# print(line,line[4],line[4]==str(id))
			if str(user) not in line[0]:
				lines.append(line)
			else:
				if str(id) not in line[4]:
					lines.append(line)
				else:
					done = f"Removed reminder of id `{id}` successfully"
		f.seek(0)
		f.truncate()
		writer = csv.writer(f,delimiter="-")
		writer.writerows(lines)
	return done


def check_remind() -> tuple | bool:
	with open("tasks.csv","r") as f:
		reader = csv.reader(f,delimiter="-")
		for line in reader:
			if time.time() > int(line[1]):
				return int(line[0]),int(line[2]),line[3],line[4],line[5]
	return False

def user_check_remind(user: int,id: int) -> tuple | str:
	amount = 0
	ids = ""
	reminder = ""
	with open("tasks.csv","r") as f:
		reader = csv.reader(f,delimiter="-")
		for line in reader:
			if str(user) in line[0]:
				ids += f"{line[4]} "
				amount += 1
				if str(id) in line[4]:
					reminder = line[1],line[3]
				# reminder = f"You have a reminder for <t:{line[1]}> of id `{id}` with reason: {line[3]}.\nTotal reminders = {amount}"
		if reminder:
			return f"You have a reminder for <t:{reminder[0]}> of id {id} with reason: {reminder[1]}\nTotal reminders = {amount}"
	if not ids:
		ids = "No reminders"
	return False,ids

# remove_reminder("holyhosting")

# print(add_remind("holyhosting",minutes=1))



# with open("names.csv","a",newline="") as f:
# 	writer = csv.writer(f,delimiter="-")
# 	writer.writerow(["hi","how","are- youx"])
# 	writer.writerow(["hi","how","are youd"])
# 	writer.writerow(["hi","how","are youe"])

# with open("names.csv","r") as f:
# 	reader = csv.reader(f,delimiter="-")
# 	for line in reader:
# 		print(line)