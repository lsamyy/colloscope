from flask import Flask, render_template, request
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# Utiliser des chemins relatifs pour accéder aux fichiers JSON
base_path = os.path.dirname(os.path.abspath(__file__))
colloscope_path = os.path.join(base_path, 'data', 'colloscope.json')
map_colles_path = os.path.join(base_path, 'data', 'map_colles.json')
map_weeks_path = os.path.join(base_path, 'data', 'map_weeks.json')

# Charger les données JSON avec encodage UTF-8
with open(colloscope_path, encoding='utf-8') as f:
    colloscope = json.load(f)

with open(map_colles_path, encoding='utf-8') as f:
    map_colles = json.load(f)

with open(map_weeks_path, encoding='utf-8') as f:
    map_weeks = json.load(f)

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
    # Si la date est déjà formatée en JJ/MM/YYYY, ne pas la reformater
    if '/' in date_str:
        return date_str
    # Sinon, formater la date de YYYY-MM-DD en JJ/MM/YYYY
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%d/%m/%Y")

# Fonction pour déterminer la semaine actuelle
def get_current_week():
    today = datetime.today()
    # Aller jusqu'au samedi précédent
    start_of_week = today - timedelta(days=today.weekday() + 2)
    end_of_week = start_of_week + timedelta(days=6)  # Fin vendredi de cette semaine
    return start_of_week, end_of_week

# Marquer la semaine actuelle pour surligner dans l'interface
def mark_current_week(weeks):
    current_start, current_end = get_current_week()  # Obtenir la semaine actuelle
    for week_key, data in weeks.items():
        # Convertir les dates en objets datetime pour les comparer, en s'assurant qu'elles sont bien au format YYYY-MM-DD
        try:
            start_date = datetime.strptime(data['start_date'], "%Y-%m-%d")
            end_date = datetime.strptime(data['end_date'], "%Y-%m-%d")
        except ValueError:
            # Si les dates sont déjà en JJ/MM/YYYY, les ignorer
            continue

        # Vérifier si la semaine courante correspond à la semaine en cours
        if start_date <= current_start <= end_date or start_date <= current_end <= end_date:
            data['highlight'] = True  # Marquer cette semaine comme la semaine actuelle
        else:
            data['highlight'] = False  # Sinon, pas de surlignage
    return weeks

# Exclure les semaines de vacances et de concours blancs
def exclure_semaines_speciales(weeks):
    semaines_filtrees = {}
    for week_key, data in weeks.items():
        if 'Concours blanc' not in data['notes'] and 'vacances' not in data['notes'].lower():
            # Formater les dates seulement si elles sont encore au format YYYY-MM-DD
            data['start_date'] = formater_date(data['start_date'])
            data['end_date'] = formater_date(data['end_date'])
            semaines_filtrees[week_key] = data
    return semaines_filtrees

@app.route('/')
def index():
    # Exclure les semaines de concours blancs et vacances
    filtered_weeks = exclure_semaines_speciales(map_weeks)
    # Marquer la semaine actuelle dans les semaines filtrées
    filtered_weeks = mark_current_week(filtered_weeks)
    return render_template('index.html', weeks=filtered_weeks)


@app.route('/planning', methods=['POST'])
def planning():
    group = request.form['group']  # Obtenir le groupe sélectionné
    selected_iso_week = request.form.get('iso_week')  # Obtenir la semaine ISO sélectionnée

    # Convertir le numéro de semaine ISO en entier
    iso_week_number = int(selected_iso_week)

    # Trouver la semaine de colle correspondante
    colloscope_week, week_data = get_colloscope_week_from_iso(iso_week_number)

    if colloscope_week is None:
        return "Aucune donnée disponible pour la semaine sélectionnée."

    # Récupérer les créneaux pour le groupe et la semaine de colle trouvée
    schedule_for_week = colloscope.get(group, {}).get(colloscope_week, [])

    if not schedule_for_week:
        return f"Aucun créneau trouvé pour le groupe {group} et la semaine {colloscope_week}."

    # Récupérer les détails des créneaux depuis map_colles.json
    detailed_schedule = []
    for creneau in schedule_for_week:
        if creneau in map_colles:
            detailed_schedule.append(map_colles[creneau])

    # Trier les créneaux par jour et heure
    detailed_schedule = trier_creneaux_par_jour_et_heure(detailed_schedule)

    return render_template('planning.html', schedule=detailed_schedule, group=group, week=week_data)

if __name__ == '__main__':
    app.run(debug=True)
