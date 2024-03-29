# XML to CSV converter
# For use with (a) musical Arduino application
# Converts Musescore output into many CSV files depending on parts
# Ethan Snyder, 3/28/2024

'''
CSV key:
       0                  1              2              3             4             5                   6
part_id       stave      note     chord     type   duration     tempo

part_id:  Listed in order of top -> bottom as MuseScore presents the parts. P1, P2, P3...
stave: 1 represents highest clef, 2 next highest, etc. Set to 0 for single-clef parts.
note: Tone, sharp/no sharp, octave.
chord: 1 represents this note belonging to the same chord/beat as the note before. 0 is default.
type: Take the inverse of these numbers to get the fraction of a measure this note lasts.
duration: XML/MuseScore secret I guess. Maybe self explanatory?
tempo: Usually 0, but checks every measure regardless for a tempo change. Gives tempo as int.
--------------------------------------------------------------------------------------------------------
dataSaver CSV key:
   0              1              2               3                 4
note     chord     type   duration     tempo

note: Tone, sharp/no sharp, octave.
chord: 1 represents this note belonging to the same chord/beat as the note before. 0 is default.
type: Take the inverse of these numbers to get the fraction of a measure this note lasts.
duration: XML/MuseScore secret I guess. Maybe self explanatory?
tempo: Usually 0, but checks every measure regardless for a tempo change. Gives tempo as int.
'''

import csv
from numpy import *
import xml.etree.ElementTree as ET

# Names of parts to exclude.	This does need to be exact. This is all near the top of the XML file.
excludePart = ["Drumset"]

# Since parts are split, dataSaver removes part and stave information from CSV file.
# XXX If you use this, please name the CSV files correctly!
dataSaver = True

def parseXML(xmlfile, exclusions):
	tree = ET.parse(xmlfile) # create element tree object
	root = tree.getroot() # get root element
	
	# Note that this block here must change in order to account for part groups (like drums).
	# I do not want this functionality right now, though.
	excludedPartIDs = []
	if (len(exclusions) > 0): # If there are parts to be excluded...
		for part in exclusions: # Iterate through the specified parts in exclusion list
			for candidate in root.findall("./part-list/score-part"): # Iterate through all parts in XML file
				if part == candidate.find("part-name").text: # If they're the same,
					excludedPartIDs = append(excludedPartIDs, [candidate.get("id")], 0) # Record the ID
					print("Excluding " + candidate.find("part-name").text + " part | " + candidate.get("id"))
				else:
					print("Including " + candidate.find("part-name").text + " part | " + candidate.get("id"))
					continue
	else:
		excludedPartIDs = []
	
	partDetails = []
	staveDetails = []
	noteDetails = []
	chordDetails = []
	typeDetails = []
	durationDetails = []
	tempoDetails = []
	#articulationDetails = [] TODO: articulations?

	
	print("Entering main processing loop...")
	#MAIN LOOP
	# Parts
	for part in root.findall("./part"):
	
		if part.get("id") in excludedPartIDs:
			continue # If we're on a part that is on the exclusion list, move on to the next part.
			
		partName = part.get("id") # Snag the part name every time the part changes
		
		# Note, duration, and voice information
		for measure in part.findall("./measure"):
		
			# Finds the tempo as QUARTER notes per minute. TODO: Add support for other expressions
			# of tempo.		
			try:
				tempo = measure.find("direction").find("direction-type").find("metronome").find("per-minute").text
			except:
				tempo = 0
		
			for note in measure.findall("./note"):
			
				# Labels the part that is being parsed
				partDetails = append(partDetails, [partName])
				
				# Labels the stave of that part that is being parsed
				try: # If there are many
					staveDetails = append(staveDetails, [note.find("staff").text])
				except: # But if not,
					staveDetails = append(staveDetails, [0]) # Slap a 0 on it
			
				try: # Pitch + Octave
					pitch = note.find("pitch").find("step").text # Find the pitch...
					octave = note.find("pitch").find("octave").text # Find the octave...
					alter = note.find("pitch").find("alter").text # Flat or sharp?
					
					pitchedNote = noteFinder(pitch, octave, alter) # Concatenate these...
					noteDetails = append(noteDetails, [pitchedNote]) # Append them to array as one item
				except: # But sometimes there's no notes in a measure
					noteDetails = append(noteDetails, [0]) # Which we signal with a 0
					
				try: # Is this note a chord with the previous note?
					note.find("chord")
					chordDetails = append(chordDetails, [1])
				except: # No?
					chordDetails = append(chordDetails, [0])
					
				# noteType is quarter, eighth, 16th, ect...
				try:
					noteType = note.find("type").text
					typeDetails = append(typeDetails, [durationFinder(noteType)])
				except:
					typeDetails = append(typeDetails, [0])
					
				duration = note.find("duration").text # Everything has a duration
				durationDetails = append(durationDetails, [duration], 0) # So we record that no matter what
				
				# This was found before, once per measure, not per note
				tempoDetails = append(tempoDetails, [tempo])
			
	# Compile all data into one big array of arrays
	masterInfoArray = stack((partDetails, staveDetails, noteDetails, chordDetails, typeDetails, durationDetails, tempoDetails), axis = 1)
	
	return masterInfoArray
		
def noteFinder(pitch, octave, alter):
	
	if alter == str(-1):  # Flat
		semitone = "b"
	elif alter == str(1): # Sharp
		semitone = "S"
	
	# Sets up a note for the match statement coming up, notes are of the form "Ab", "GS".
	note = pitch + semitone
	
	# Convert all flats into sharps, that's how the Arduino pitches.h likes it. Also correct semi-tone issues
	# around B, C, E, F.
	match note:
		case "Ab":
			note = "GS"
			octave = str(int(octave) - 1) # Ab = G# in the lower octave
		case "Bb":
			note = "AS"
		case "BS":
			note = "C"
		case "Cb":
			note = "B"
		case "Db":
			note = "CS"
		case "Eb":
			note = "DS"
		case "ES":
			note = "F"
		case "Fb":
			note = "E"
		case "Gb":
			note = "FS"
	
	return note + octave
	
def durationFinder(noteType):
	match noteType:
		case "whole":
			return 1
		case "half":
			return 2
		case "quarter":
			return 4
		case "eighth":
			return 8
		case "16th":
			return 16
		case "32nd":
			return 32
		case _:
			return int(0)

def isolatePart(writeable, isoString, isoIndex):
	returnable = []
	cache = []
	
	for elem in writeable:
		if str(elem[isoIndex]) == isoString:
			returnable.append(elem)
	
	return returnable
			
def saveToCSV(writeable, filename):

	temp = []
	if dataSaver == True:
		for row in writeable:
			temp.append(row[2:])
		writeable = temp
		
	with open(filename, 'w', newline='') as csvfile:
			writer = csv.writer(csvfile)
			for row in writeable:
				writer.writerow([row])
				
	print(filename + " saved!")
	
def main():
	xmlArray = parseXML('score.xml', excludePart) # Heavy duty number crunching only once
	
	p1 = isolatePart(xmlArray, "P1", 0)
	p1treble = isolatePart(p1, "1", 1)
	p1bass = isolatePart(p1, "2", 1)
	
	saveToCSV(p1treble, "PianoTreble.csv")
	saveToCSV(p1bass, "PianoBass.csv")
	
	p3 = isolatePart(xmlArray, "P3", 0)
	saveToCSV(p3, "Basspart.csv")
	
main()
