from flask import Flask, render_template, request
import json
import os
from datetime import datetime, timedelta
import locale
from babel.dates import format_date

app = Flask(__name__)

# Définir la locale en français pour le formatage des dates
locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

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

# Fonction pour formater une date en français de manière lisible
def formater_date_humaine(date_str):
    # Parse la date dans le format DD/MM/YYYY
    date_obj = datetime.strptime(date_str, "%d/%m/%Y")
    # Utiliser Babel pour reformater la date en français
    formatted_date = format_date(date_obj, format='full', locale='fr_FR')
    return formatted_date.capitalize()

# Fonction pour trier les DS par date
def trier_ds_par_date(ds_data):
    return sorted(ds_data.items(), key=lambda ds: datetime.strptime(ds[1]['date'], "%Y-%m-%d"))

# Fonction pour obtenir la semaine de colle correspondant à une semaine ISO
def get_colloscope_week_from_iso(iso_week_number):
    for week_key, data in map_weeks.items():
        if data["iso_week"] == iso_week_number:
            return week_key, data
    return None, None

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

# Marquer la semaine actuelle pour surligner dans l'interface
def mark_current_week(weeks):
    current_start, current_end = get_current_week()
    for week_key, data in weeks.items():
        try:
            start_date = datetime.strptime(data['start_date'], "%Y-%m-%d")
            end_date = datetime.strptime(data['end_date'], "%Y-%m-%d")
        except ValueError:
            continue

        if start_date <= current_start <= end_date or start_date <= current_end <= end_date:
            data['highlight'] = True
        else:
            data['highlight'] = False
    return weeks

# Exclure les semaines de vacances, concours blancs et celles déjà passées
def exclure_semaines_speciales(weeks):
    semaines_filtrees = {}
    current_date = datetime.today()  # Get current date
    for week_key, data in weeks.items():
        # Check if the date is in DD/MM/YYYY format and convert it back to YYYY-MM-DD for parsing
        if '/' in data['end_date']:  # This checks if the date is already formatted
            end_date = datetime.strptime(data['end_date'], "%d/%m/%Y")
        else:
            end_date = datetime.strptime(data['end_date'], "%Y-%m-%d")

        if end_date >= current_date and 'Concours blanc' not in data['notes'] and 'vacances' not in data['notes'].lower():
            data['start_date'] = formater_date(data['start_date'])
            data['end_date'] = formater_date(data['end_date'])
            semaines_filtrees[week_key] = data
    return semaines_filtrees


@app.route('/')
def index():
    # Exclure les semaines déjà passées, concours blancs et vacances
    filtered_weeks = exclure_semaines_speciales(map_weeks)
    # Marquer la semaine actuelle
    filtered_weeks = mark_current_week(filtered_weeks)
    return render_template('index.html', weeks=filtered_weeks)

@app.route('/planning', methods=['POST'])
def planning():
    group = request.form['group']
    selected_iso_week = request.form.get('iso_week')

    iso_week_number = int(selected_iso_week)

    colloscope_week, week_data = get_colloscope_week_from_iso(iso_week_number)

    if colloscope_week is None:
        return "Aucune donnée disponible pour la semaine sélectionnée."

    schedule_for_week = colloscope.get(group, {}).get(colloscope_week, [])

    if not schedule_for_week:
        return f"Aucun créneau trouvé pour le groupe {group} et la semaine {colloscope_week}."

    detailed_schedule = []
    for creneau in schedule_for_week:
        if creneau in map_colles:
            detailed_schedule.append(map_colles[creneau])

    detailed_schedule = trier_creneaux_par_jour_et_heure(detailed_schedule)

    return render_template('planning.html', schedule=detailed_schedule, group=group, week=week_data)

@app.route('/ds')
def afficher_planning_ds():
    # Charger les DS depuis un fichier JSON
    ds_path = os.path.join(base_path, 'data', 'ds.json')
    with open(ds_path, encoding='utf-8') as f:
        ds = json.load(f)

    # Trier les DS par date et heure de fin (toujours dans le format 'DD/MM/YYYY')
    ds_trie = sorted(ds.values(), key=lambda x: datetime.strptime(x['date'] + ' ' + x['heure_fin'], '%d/%m/%Y %H:%M'))

    # Obtenir l'heure actuelle
    maintenant = datetime.now()

    # Trouver le prochain DS dont l'heure de fin est dans le futur
    prochain_ds_index = None
    for i, d in enumerate(ds_trie):
        # Combiner la date et l'heure de fin pour chaque DS
        ds_datetime_fin = datetime.strptime(d['date'] + ' ' + d['heure_fin'], '%d/%m/%Y %H:%M')
        # Vérifier si la fin du DS est après maintenant
        if ds_datetime_fin > maintenant:
            prochain_ds_index = i
            break  # Sortir dès qu'on trouve le premier DS dans le futur

    # Si aucun DS futur n'est trouvé, ne surligner aucun DS
    if prochain_ds_index is None:
        prochain_ds_index = 0

    # Formater la date pour chaque DS en "Lundi 14 octobre 2024"
    for ds_value in ds_trie:
        ds_value['date_affichee'] = formater_date_humaine(ds_value['date'])

    return render_template('ds.html', ds=ds_trie, prochain_ds_index=prochain_ds_index)



if __name__ == '__main__':
    app.run(debug=True)