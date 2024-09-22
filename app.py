from flask import Flask, render_template, request, redirect, flash
import json
import os
from datetime import datetime, timedelta
from babel.dates import format_date

app = Flask(__name__)

# Utiliser des chemins relatifs pour accéder aux fichiers JSON
base_path = os.path.dirname(os.path.abspath(__file__))
colloscope_path = os.path.join(base_path, 'data', 'colloscope.json')
map_colles_path = os.path.join(base_path, 'data', 'map_colles.json')
map_weeks_path = os.path.join(base_path, 'data', 'map_weeks.json')
ds_path = os.path.join(base_path, 'data', 'ds.json')

# Charger les données JSON avec encodage UTF-8
with open(colloscope_path, encoding='utf-8') as f:
    colloscope = json.load(f)

with open(map_colles_path, encoding='utf-8') as f:
    map_colles = json.load(f)

with open(map_weeks_path, encoding='utf-8') as f:
    map_weeks = json.load(f)

with open(ds_path, encoding='utf-8') as f:
    ds_data = json.load(f)

# Dictionnaire pour trier les jours de la semaine
jours_ordre = {
    "Lundi": 1,
    "Mardi": 2,
    "Mercredi": 3,
    "Jeudi": 4,
    "Vendredi": 5,
    "Samedi": 6,
    "Dimanche": 7
}

# Function to format dates in French using babel
def formater_date_humaine(date_str):
    date_obj = datetime.strptime(date_str, "%d/%m/%Y")
    formatted_date = format_date(date_obj, format='full', locale='fr_FR')
    return formatted_date.capitalize()

# New function to handle both date formats
def parse_date_flexible(date_str):
    """Parses date string in either YYYY-MM-DD or DD/MM/YYYY format."""
    try:
        # Try parsing in YYYY-MM-DD format first
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        # Fallback to DD/MM/YYYY format
        return datetime.strptime(date_str, "%d/%m/%Y")

# Fonction pour trier les créneaux par jour de la semaine et heure
def trier_creneaux_par_jour_et_heure(detailed_schedule):
    return sorted(detailed_schedule, key=lambda creneau: (jours_ordre[creneau['jour']], creneau['heure']))

# Fonction pour formater les dates en JJ/MM/YYYY
def formater_date(date_str):
    if '/' in date_str:
        return date_str
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%d/%m/%Y")

# Fonction pour déterminer la semaine actuelle
def get_current_week():
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday() + 2)
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week, end_of_week

def get_upcoming_colle_in_week(week_schedule):
    maintenant = datetime.now()

    for i, colle in enumerate(week_schedule):
        colle_datetime = datetime.strptime(colle['date'] + ' ' + colle['heure'], '%d/%m/%Y %H:%M')
        if colle_datetime > maintenant:
            return i  # Return the index of the closest upcoming colle
    return -1  # No upcoming colle, return -1

# Fonction pour obtenir la semaine la plus proche avec des colles futures
def get_upcoming_week(weeks, detailed_schedule):
    maintenant = datetime.now()

    for i, week_schedule in enumerate(detailed_schedule):
        for colle in week_schedule:
            # Ensure colle is a dictionary and has 'date' and 'heure'
            if isinstance(colle, dict) and 'date' in colle and 'heure' in colle:
                try:
                    colle_datetime = datetime.strptime(colle['date'] + ' ' + colle['heure'], '%d/%m/%Y %H:%M')
                    if colle_datetime > maintenant:
                        return i
                except ValueError as e:
                    print(f"Error parsing colle date/time: {e}")
                    continue

    return 0  # Default to the first week if no future colles are found

# Function to check and add events (position them between the relevant weeks)
def get_event_for_week(current_week_start, next_week_start):
    events = [
        {"title": "Vacances de la Toussaint", "start": "2024-10-21", "end": "2024-11-03"},
        {"title": "Concours Blanc 1", "start": "2024-12-16", "end": "2024-12-22"},
        {"title": "Vacances de Noël", "start": "2024-12-23", "end": "2025-01-05"},
        {"title": "Vacances d'Hiver", "start": "2025-02-17", "end": "2025-03-02"},
        {"title": "Concours Blanc 2", "start": "2025-03-03", "end": "2025-03-09"},
        {"title": "Vacances de Printemps", "start": "2025-04-14", "end": "2025-04-27"}
    ]

    # Convert week start dates to datetime objects
    current_week_start = parse_date_flexible(current_week_start)
    next_week_start = parse_date_flexible(next_week_start)

    event_titles = []  # Store all events in case there are consecutive ones

    for event in events:
        event_start = parse_date_flexible(event['start'])
        event_end = parse_date_flexible(event['end'])

        # Place event between current and next week
        if current_week_start < event_start < next_week_start:
            event_titles.append(event["title"])

    # Return all event titles if found, otherwise None
    return event_titles if event_titles else None






# Exclure les semaines sans colles et celles déjà passées
from datetime import datetime, timedelta

# Determine the current week and whether it is after Friday 21:00
def is_past_friday_night():
    # Get the current time on the server (Oregon time)
    now = datetime.now()

    # Adjust for Paris time (UTC+2 during daylight saving)
    paris_time = now + timedelta(hours=8)

    # Log current server and Paris time for debugging
    print(f"Current server time: {now}")
    print(f"Paris adjusted time: {paris_time}")

    # Check if it's Friday after 21:00 in Paris time or it's the weekend (Saturday or Sunday)
    if paris_time.weekday() == 4 and paris_time.hour >= 21:  # After 21:00 on Friday
        return True
    elif paris_time.weekday() > 4:  # If it's Saturday or Sunday
        return True
    else:
        return False


def filter_weeks_with_colles(group):
    filtered_weeks = {}
    detailed_schedule_by_week = []
    upcoming_week_found = False
    previous_week_data = None  # Track the previous week's data

    # Iterate through all weeks in the schedule
    for week_key, week_data in map_weeks.items():
        colles_for_week = colloscope.get(group, {}).get(week_key, [])
        if not colles_for_week:
            continue  # Skip weeks with no colles

        week_schedule = []
        for colle_id in colles_for_week:
            colle_info = map_colles.get(colle_id)
            if colle_info:
                colle_info_copy = colle_info.copy()
                colle_info_copy['date'] = formater_date(week_data['start_date'])
                colle_info_copy['salle'] = colle_info.get('salle', None)
                week_schedule.append(colle_info_copy)

        # Sort colles by day and time
        if week_schedule:
            week_schedule = trier_creneaux_par_jour_et_heure(week_schedule)

            # Add event if present between weeks
            event = None
            if previous_week_data:
                event = get_event_for_week(previous_week_data['start_date'], week_data['start_date'])

            # Initialize is_upcoming_week to False at the start of each loop
            is_upcoming_week = False

            # Check if this is the upcoming week based on the Paris time logic
            if not upcoming_week_found:
                week_start = parse_date_flexible(week_data['start_date'])
                week_end = parse_date_flexible(week_data['end_date'])
                now = datetime.now() + timedelta(hours=8)  # Adjust server time to Paris time

                if week_start <= now <= week_end and not is_past_friday_night():
                    upcoming_week_found = True
                    is_upcoming_week = True
                elif week_start > now or (week_start <= now <= week_end and is_past_friday_night()):
                    upcoming_week_found = True
                    is_upcoming_week = True

            filtered_weeks[week_key] = week_data
            detailed_schedule_by_week.append((week_key, week_schedule, event, is_upcoming_week))

        previous_week_data = week_data

    return filtered_weeks, detailed_schedule_by_week













@app.route('/')
def index():
    return render_template('index.html')

@app.route('/planning', methods=['POST'])
def planning():
    group = request.form['group']

    # Get filtered weeks and detailed schedule for the group
    filtered_weeks, detailed_schedule_by_week = filter_weeks_with_colles(group)
    
    maintenant = datetime.now()
    prochain_creneau_index = -1  # Default to -1 if no future week found

    detailed_schedule_with_flags = []

    for entry in detailed_schedule_by_week:
        # Unpack the regular week data (4-tuple now)
        week_key, week_colles, event, is_upcoming_week = entry
        week_colles_with_flags = []

        for colle_index, colle in enumerate(week_colles):
            colle_datetime = datetime.strptime(colle['date'] + ' ' + colle['heure'], '%d/%m/%Y %H:%M')

            if colle_datetime > maintenant and prochain_creneau_index == -1:
                # This is the first future colle, mark the week and the colle as upcoming
                prochain_creneau_index = len(detailed_schedule_with_flags)
                week_colles_with_flags.append({
                    'data': colle,
                    'is_upcoming_colle': True
                })
            else:
                week_colles_with_flags.append({
                    'data': colle,
                    'is_upcoming_colle': False
                })

        # Ensure there are two colles (or insert a placeholder)
        if len(week_colles_with_flags) < 2:
            week_colles_with_flags.append({
                'data': {
                    'matiere': 'Inconnu',
                    'professeur': 'inconnu',
                    'jour': 'Dimanche',
                    'heure': '00:00',
                    'salle': 'inconnue'
                },
                'is_upcoming_colle': False
            })

        detailed_schedule_with_flags.append({
            'week_key': week_key,
            'week_colles': week_colles_with_flags,
            'is_upcoming_week': is_upcoming_week,
            'event': event,
            'is_event_divider': False  # It's not an event divider
        })

    return render_template(
        'planning.html',
        schedule=detailed_schedule_with_flags,
        group=group,
        weeks=filtered_weeks,
        prochain_creneau_index=prochain_creneau_index
    )




@app.route('/ds')
def afficher_planning_ds():
    ds_trie = sorted(ds_data.values(), key=lambda x: datetime.strptime(x['date'] + ' ' + x['heure_fin'], '%d/%m/%Y %H:%M'))
    maintenant = datetime.now()

    prochain_ds_index = None
    for i, d in enumerate(ds_trie):
        ds_datetime_fin = datetime.strptime(d['date'] + ' ' + d['heure_fin'], '%d/%m/%Y %H:%M')
        if ds_datetime_fin > maintenant:
            prochain_ds_index = i
            break

    if prochain_ds_index is None:
        prochain_ds_index = 0

    for ds_value in ds_trie:
        ds_value['date_affichee'] = formater_date_humaine(ds_value['date'])

    return render_template('ds.html', ds=ds_trie, prochain_ds_index=prochain_ds_index)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/updates')
def updates():
    with open(os.path.join(base_path, 'data', 'updates.json'), encoding='utf-8') as f:
        updates_data = json.load(f)['updates']  # Ensure we're accessing the "updates" key
    
    # Sort updates by date (newest first) and format date to DD-MM-YYYY
    sorted_updates = sorted(updates_data, key=lambda x: x['date'], reverse=True)
    
    for update in sorted_updates:
        # Convert date format from YYYY-MM-DD to DD-MM-YYYY
        update['date'] = datetime.strptime(update['date'], "%Y-%m-%d").strftime("%d-%m-%Y")
    
    return render_template('updates.html', updates=sorted_updates)


if __name__ == '__main__':
    app.run(debug=True)
