import fire
import psycopg2
import csv
import os


VACCINE_TYPE = {"COM": "Pfizer/BioNTech", "MOD": "Moderna", "CN": "SinoPharm", "SIN": "Coronavac – Sinovac", "JANSS": "J&J Janssen", "SPU": "Sputnik V", "AZ": "AstraZeneca", "UNK": "Unknown" }
COUNTRY_CODES = {
    "BE": "Belgium", "BG": "Bulgaria", 
    "CZ": "Czechia", 
    "FR": "France", 
    "DK": "Denmark", "DE": "Germany",
    "EE": "Estonia",
    "IE": "Ireland",
    "EL": "Greece",
    "ES": "Spain",
    "HR": "Croatia",
    "IT": "Italy",
    "CY": "Cypress",
    "LV": "Latvia",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "HU": "Hungary",
    "MT": "Malta",
    "NL": "Netherlands",
    "AT": "Austria",
    "PL": "Poland", "PT": "Portugal",
    "RO": "Romania",
    "SI": "Slovenia", "SK":"Slovakia",
    "FI": "Finland",
    "SE": "Sweden",
    "IS": "Iceland",
    "LI": "Leichtenstein",
    "CH": "Switzerland",
    "NO": "Norway",
    "UK": "United Kingdom"
    }

def writeConfig(conn_string):
    with open(".conninfo","w") as source:
        source.write(conn_string)
        return "Successfully wrote config file"

def get_env(env_variable):
    try:
        return os.environ[env_variable]
    except KeyError:
        error_msg = f"Set the {env_variable} environment variable"
        raise KeyError

CONNECTION_STRING = get_env("CONNECTION_STRING")

def connect():
    connString=CONNECTION_STRING
    try:
        conn=psycopg2.connect(connString)
        return conn
    except:
        print("Database connection error - is your connectionString set properly in Configuration Settings?")
        return None

'''
The headers for the CSV are as follows. 
More information is present here: https://www.ecdc.europa.eu/sites/default/files/documents/Variable_Dictionary_VaccineTracker-03-2021.pdf
YearWeekISO,FirstDose,FirstDoseRefused, SecondDose,UnknownDose,NumberDosesReceived,Region,Population,ReportingCountry,TargetGroup,Vaccine,Denominator
'''

def loadData(filename="covid_data.csv"):
    conn=connect()
    cursor=conn.cursor()
    cursor.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    cursor.execute('DROP TABLE IF EXISTS raw_data')
    cursor.execute('DROP TABLE IF EXISTS vaccine_data')
    cursor.execute('CREATE TABLE raw_data(YearWeekISO text,FirstDose bigint, FirstDoseRefused bigint, SecondDose bigint, UnknownDose bigint, NumberDosesReceived bigint, Region text,Population text, ReportingCountry text, TargetGroup text, Vaccine text, Denominator text);')
    cursor.execute('CREATE TABLE vaccine_data(NumberDosesReceived bigint, ReportingCountry text, Vaccine text);')

    conn.commit()
    with open(filename,'r') as incoming:
        cursor.copy_expert('COPY raw_data FROM stdin CSV',incoming)
        conn.commit()
        return "Data loaded successfully"

def populateVaccineData():
    conn=connect()
    cursor=conn.cursor()
    cursor.execute('INSERT INTO vaccine_data SELECT NumberDosesReceived,ReportingCountry,Vaccine FROM raw_data')
    conn.commit()
    return None

def getAllData():
    ret=dict()
    conn=connect()
    cursor=conn.cursor()
    cursor.execute('SELECT * FROM vaccine_list')
    for entry in cursor.fetchall():
        device=entry[0]
        data=entry[1]
        if device not in ret:
            ret[device]=[]
        ret[device].append(data)
    return ret

def getCountryVaccinePercentages():
    vaccine_dose_counts = getCountryVaccineCounts()
    for country in vaccine_dose_counts.keys():
        total_doses = vaccine_dose_counts[country]["total_doses"]
        total_percentage = 0
        for vaccine_type in vaccine_dose_counts[country].keys():
            if vaccine_type == "total_doses" or total_doses == 0:
                pass
            else:
                percentage = vaccine_dose_counts[country][vaccine_type] * 100/(1.0 * total_doses)
                percentage = round(percentage,2)
                vaccine_dose_counts[country][vaccine_type] = percentage
                total_percentage += percentage
        del vaccine_dose_counts[country]["total_doses"]
    return vaccine_dose_counts

def getCountryVaccineCounts():
    summary_information = dict()
    conn=connect()
    cursor=conn.cursor()
    cursor.execute('SELECT distinct NumberDosesReceived, ReportingCountry, Vaccine FROM vaccine_data')
    conn.commit()
    for entry in cursor.fetchall():
        doses, country, vaccine_type=entry
        if country in COUNTRY_CODES:
            country = COUNTRY_CODES[country]
        if vaccine_type in VACCINE_TYPE:
            vaccine_type = VACCINE_TYPE[vaccine_type]
        if doses == None:
            doses = 0
        if country not in summary_information:
            summary_information[country] = {vaccine_type: doses, "total_doses": doses}
        else:
            if vaccine_type not in summary_information[country]:
                summary_information[country][vaccine_type] = doses
                summary_information[country]["total_doses"] += doses
            else:
                try:
                    summary_information[country][vaccine_type] += int(doses)
                    summary_information[country]["total_doses"] += doses

                except:
                    print("An error occurred")
                    print(doses, country, vaccine_type)
    return summary_information

if __name__ == '__main__':
    fire.Fire({"writeConfig":writeConfig,"loadData":loadData,"getAllData": getAllData, "populateVaccineData": populateVaccineData, "getCountryVaccineCounts":getCountryVaccineCounts, "getCountryVaccinePercentages": getCountryVaccinePercentages})
