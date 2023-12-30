import csv
import os, json
from collections import OrderedDict
from csv import DictWriter, DictReader, writer
from datetime import datetime, timedelta

import sys

from garminconnect import Garmin

hrv_file = "hrv_dump.csv"
hrv_file_json = "hrv_dump.json"


# Function to generate a list of dates for the last two years in the format YYYY-MM-DD
def generate_date_list():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 2)
    date_list = []

    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)

    return date_list


# Load environment variables if defined
email = os.getenv("EMAIL")
password = os.getenv("PASSWORD")
tokenstore = os.getenv("GARMINTOKENS") or "~/.garminconnect"
api = None


def fetch_from_garmin():
    garmin = Garmin()
    garmin.login(tokenstore)

    all_dates = generate_date_list()

    last_two_years = []

    for day in all_dates:
        hrv_data = garmin.get_hrv_data(day)
        sleep_data = garmin.get_sleep_data(day)
        spo2_data = garmin.get_spo2_data(day)
        resp_data = garmin.get_respiration_data(day)
        stress_data = garmin.get_all_day_stress(day)

        last_two_years.append(
            dict(
                day=day,
                hrv=hrv_data,
                sleep=sleep_data,
                spo2=spo2_data,
                resp=resp_data,
                stress=stress_data,
            )
        )

        print(f"Fetched {day}")

    with open(hrv_file, "w") as f:
        writer = DictWriter(
            f, fieldnames=["day", "hrv", "sleep", "spo2", "resp", "stress"]
        )
        writer.writeheader()
        writer.writerows(last_two_years)


def raw_to_json(bad_json: str) -> str:
    return json.loads(
        bad_json.replace("'", '"')
        .replace("None", "null")
        .replace("True", "true")
        .replace("False", "false")
    )


def process_and_export_stats():
    csv.field_size_limit(sys.maxsize)

    with open(hrv_file, "r") as f:
        reader = DictReader(f)

        to_write = []

        for row in reader:
            day, hrv, sleep, spo2, resp, stress = (
                row["day"],
                row["hrv"],
                row["sleep"],
                row["spo2"],
                row["resp"],
                row["stress"],
            )
            spreadsheet_data = dict(Day=day)

            if hrv:
                hrv_data = raw_to_json(hrv)

                spreadsheet_data["HRV: Weekly Average"] = hrv_data["hrvSummary"][
                    "weeklyAvg"
                ]
                spreadsheet_data["HRV: Last Night Average"] = hrv_data["hrvSummary"][
                    "lastNightAvg"
                ]
                spreadsheet_data["HRV: Last Night 5 Minute High"] = hrv_data[
                    "hrvSummary"
                ]["lastNight5MinHigh"]
                spreadsheet_data["HRV: Status"] = hrv_data["hrvSummary"]["status"]

                if (
                    "baseline" in hrv_data["hrvSummary"]
                    and hrv_data["hrvSummary"]["baseline"]
                ):
                    spreadsheet_data["HRV: Baseline Range Low Upper"] = hrv_data[
                        "hrvSummary"
                    ]["baseline"]["lowUpper"]
                    spreadsheet_data["HRV: Baseline Range Balanced Low"] = hrv_data[
                        "hrvSummary"
                    ]["baseline"]["balancedLow"]
                    spreadsheet_data["HRV: Baseline Range Balanced Upper"] = hrv_data[
                        "hrvSummary"
                    ]["baseline"]["balancedUpper"]

            if sleep:
                sleep_data = raw_to_json(sleep)

                spreadsheet_data["Resting Heart Rate (Sleep)"] = sleep_data.get(
                    "restingHeartRate"
                )

                if "sleepScores" in sleep_data:
                    spreadsheet_data["Sleep Score"] = (
                        sleep_data.get("sleepScores").get("overall").get("value")
                    )

                if (
                    "sleepBodyBattery" in sleep_data
                    and len(sleep_data["sleepBodyBattery"]) > 0
                ):
                    spreadsheet_data["Body Battery"] = sleep_data["sleepBodyBattery"][
                        -1
                    ]["value"]

                # spreadsheet_data["Sleep Heart Rate"] = sleep_data.get("sleepHeartRate")

            if spo2:
                spo2_data = raw_to_json(spo2)
                spreadsheet_data["Average SpO2"] = spo2_data.get("averageSpO2")

            if resp:
                resp_data = raw_to_json(resp)
                spreadsheet_data["Average Respiration Value (Sleep)"] = resp_data.get(
                    "avgSleepRespirationValue"
                )

            if stress:
                stress_data = raw_to_json(stress)
                spreadsheet_data["Average Stress Level"] = stress_data.get(
                    "avgStressLevel"
                )
                spreadsheet_data["Max Stress Level"] = stress_data.get("maxStressLevel")

            to_write.append(spreadsheet_data)

    with open("sleep_data_for_analysis.csv", "w") as f:
        output = csv.DictWriter(
            f,
            fieldnames=[
                "Day",
                "HRV: Weekly Average",
                "HRV: Last Night Average",
                "HRV: Last Night 5 Minute High",
                "HRV: Status",
                "HRV: Baseline Range Low Upper",
                "HRV: Baseline Range Balanced Low",
                "HRV: Baseline Range Balanced Upper",
                "Resting Heart Rate (Sleep)",
                "Sleep Score",
                "Body Battery",
                "Sleep Heart Rate",
                "Average SpO2",
                "Average Respiration Value (Sleep)",
                "Average Stress Level",
                "Max Stress Level",
            ],
        )
        output.writeheader()

        for row in to_write:
            print(row)
            output.writerow(row)


# fetch_from_garmin()
process_and_export_stats()
