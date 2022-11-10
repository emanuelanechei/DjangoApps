from django.shortcuts import render
from hobbits.models import *

def hobbits_index(request):
	currentStatus = CurrentStatus.load()
	summary = currentStatus.summary()
	context = {
		"summary": summary,
		"walks": formatWalks(Walk.objects.order_by('startDateTime')),
		"milestones": formatMilestones(MajorMilestone.objects.order_by('position'), summary.get('totalDistanceWalked'))
	}
	return render(request, "hobbits_index.html", context)

def hobbits_refreshData(request):
	activities = fitbitGetData()
	importFromJSON(activities)
	return hobbits_index(request)

def formatWalks(walkList):
	#from django.utils import timezone
	formattedWalks = []
	for walk in walkList:
		formattedWalks.append({
			#"startDateTime": timezone.localtime(walk.startDateTime),
			"startDateTime": walk.startDateTime,
			"distance": round(walk.distance,2),
			"duration": round(walk.duration/60000, 2), #milliseconds to minutes
			"id": walk.fitbitLogId,
		})
	return formattedWalks

def formatMilestones(msList, totalMiles):
	formattedMs = []
	for ms in msList:
		formattedMs.append({
			"position": ms.position,
			"text": ms.text,
			"distanceFromShire": round(ms.distanceFromShire,0),
			"distanceFromLastMilestone": round(ms.distanceFromLastMilestone, 0),
			"distanceRemaining": round((ms.distanceFromShire-totalMiles),2),
		})
	return formattedMs

def fitbitGetData():
	import fitbit
	from django.conf import settings
	from datetime import datetime, timedelta
	consumer_key = settings.FITBIT_CLIENTID
	consumer_secret = settings.FITBIT_CLIENTSECRET
	access_token = settings.FITBIT_ACCESS_TOKEN
	refresh_token = settings.FITBIT_REFRESH_TOKEN
	try:
		authd_client = fitbit.Fitbit(consumer_key, consumer_secret, access_token=access_token, refresh_token=refresh_token)
	except:
		return hobbits_reauth(request)

	startDate = (datetime.today()-timedelta(days=10)).strftime("%Y-%m-%d")
	activities = authd_client.activity_logs_list(after_date=startDate, limit=50).get('activities')
	authd_client.sleep()

	return activities

def hobbits_reauthFitbit(request):
	return render(request, "hobbits_reauth.html")

def importFromJSON(results):
	from dateutil import parser
	for row in results:
		if row.get('activityName')=="Walk" and row.get('logType')=="tracker" and not Walk.objects.filter(fitbitLogId=row.get('logId')).exists():
			newWalk = Walk(startDateTime=parser.parse(row.get('startTime')),
							steps=int(row.get('steps')), 
							distance=float(row.get('distance')), 
							duration=int(row.get('duration')),
							fitbitLogId=row.get('logId'))
			newWalk.save()
	currentStatus = CurrentStatus.load()
	currentStatus.update()

def legacyDataImport(request):
	import csv, os
	from dateutil import parser
	from django.conf import settings
	filepath=os.path.join( settings.STATIC_ROOT, 'hobbits/dogwalks_nonfitbit.csv' )
	with open(filepath, newline='') as csvfile:
		reader = csv.DictReader(csvfile)
		for row in reader:
			if not Walk.objects.filter(fitbitLogId=row.get('UniqueId')).exists():
				newWalk = Walk(startDateTime=parser.parse(row.get('DateTime')),
								distance=float(row.get('Miles')), 
								duration=int(row.get('Milliseconds')),
								fitbitLogId=row.get('UniqueId'))
				newWalk.save()
	currentStatus = CurrentStatus.load()
	currentStatus.update()
	return hobbits_index(request)