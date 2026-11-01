import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sqlite3
import tempfile

import pandas as pd

ROOT = Path(__file__).resolve().parent
CSV_FILE = ROOT / "spending_tracker.csv"
DB_FILE = ROOT / "data" / "spending.db"
HEADERS = ["date", "food_drink_eur", "transport_eur", "other_eur",
           "total_eur", "day_type", "data_source"]
CATEGORIES = ["food_drink_eur", "transport_eur", "other_eur"]
LABELS = ["Food and drinks", "Transport", "Other"]


def parse_date(text):
    day = datetime.strptime(text.strip(), "%d-%m-%Y").date()
    if day.strftime("%d-%m-%Y") != text.strip():
        raise ValueError("Use DD-MM-YYYY, for example 01-10-2026.")
    if not 1900 <= day.year <= 2100:
        raise ValueError("Use a year from 1900 to 2100 so date analysis is supported.")
    return day


def money_to_cents(text):
    """Store money as whole cents to avoid rounding errors."""
    text = str(text).strip()
    digits = text.replace(".", "", 1)
    if not digits.isascii() or not digits.isdecimal():
        raise ValueError("Enter a non-negative amount, for example 7.50.")
    if "." in text and len(text.split(".")[1]) > 2:
        raise ValueError("Amounts can have at most two decimal places.")
    try:
        cents = int(Decimal(text) * 100)
    except (InvalidOperation, ValueError, OverflowError):
        raise ValueError("Invalid money amount.") from None
    if cents > 9223372036854775807:
        raise ValueError("Amount is too large for the database.")
    return cents


def money_text(cents):
    return f"{cents // 100}.{cents % 100:02d}"


def validate_record(row):
    day = parse_date(row["date"])
    food = money_to_cents(row["food_drink_eur"])
    transport = money_to_cents(row["transport_eur"])
    other = money_to_cents(row["other_eur"])
    total = money_to_cents(row["total_eur"])
    if total != food + transport + other:
        raise ValueError("Total must equal food/drinks + transport + other.")
    day_type = "Weekend" if day.weekday() >= 5 else "Weekday"
    if row["day_type"].strip() != day_type:
        raise ValueError("Day type does not match the date.")
    source = row["data_source"].strip()
    if source not in ("Simulated", "Recorded"):
        raise ValueError("Data source must be Simulated or Recorded.")
    return {"date": day.isoformat(), "food_cents": food,
            "transport_cents": transport, "other_cents": other,
            "total_cents": total, "day_type": day_type, "data_source": source}


def read_records(csv_file=CSV_FILE):
    records = []
    dates = set()
    with open(csv_file, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != HEADERS:
            raise ValueError("CSV headings must be: " + ",".join(HEADERS))
        for line, row in enumerate(reader, start=2):
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("Wrong number of CSV fields.")
                record = validate_record(row)
                if record["date"] in dates:
                    raise ValueError("Duplicate date: " + row["date"])
            except (ValueError, KeyError) as error:
                raise ValueError(f"CSV line {line}: {error}") from None
            dates.add(record["date"])
            records.append(record)
    if sum(record["total_cents"] for record in records) > 9223372036854775807:
        raise ValueError("The combined spending total is too large for SQLite.")
    return sorted(records, key=lambda record: record["date"])


def connect_database(db_file=DB_FILE):
    db_file = Path(db_file)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_file)


def reload_database(csv_file=CSV_FILE, db_file=DB_FILE):
    records = read_records(csv_file)
    connection = connect_database(db_file)
    try:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS spending (
                    date TEXT PRIMARY KEY,
                    food_cents INTEGER NOT NULL CHECK(food_cents >= 0),
                    transport_cents INTEGER NOT NULL CHECK(transport_cents >= 0),
                    other_cents INTEGER NOT NULL CHECK(other_cents >= 0),
                    total_cents INTEGER NOT NULL,
                    day_type TEXT NOT NULL CHECK(day_type IN ('Weekday', 'Weekend')),
                    data_source TEXT NOT NULL CHECK(data_source IN ('Simulated', 'Recorded')),
                    CHECK(total_cents = food_cents + transport_cents + other_cents)
                )
            """)
            connection.execute("DELETE FROM spending")
            connection.executemany("""
                INSERT INTO spending VALUES
                (:date, :food_cents, :transport_cents, :other_cents,
                 :total_cents, :day_type, :data_source)
            """, records)
    finally:
        connection.close()
    return len(records)


def load_frame(db_file=DB_FILE, start=None, end=None):
    query = "SELECT * FROM spending"
    parameters = []
    if start is not None and end is not None:
        query += " WHERE date BETWEEN ? AND ?"
        parameters = [start, end]
    query += " ORDER BY date"
    connection = connect_database(db_file)
    try:
        frame = pd.read_sql_query(query, connection, params=parameters)
    finally:
        connection.close()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["food_drink_eur"] = frame["food_cents"] / 100
    frame["transport_eur"] = frame["transport_cents"] / 100
    frame["other_eur"] = frame["other_cents"] / 100
    frame["total_eur"] = frame["total_cents"] / 100
    return frame


def database_summary(db_file=DB_FILE):
    connection = connect_database(db_file)
    try:
        return connection.execute("""
            SELECT COUNT(*), COALESCE(SUM(total_cents), 0), AVG(total_cents),
                   MIN(date), MAX(date)
            FROM spending
        """).fetchone()
    finally:
        connection.close()


def category_summary(frame):
    totals = [int(frame[column].sum()) / 100
              for column in ("food_cents", "transport_cents", "other_cents")]
    result = pd.DataFrame({"category": LABELS, "total_eur": totals})
    total = sum(totals)
    result["share_percent"] = result["total_eur"] / total * 100 if total else 0.0
    return result.round(2)


def day_type_summary(db_file=DB_FILE):
    connection = connect_database(db_file)
    try:
        return pd.read_sql_query("""
            SELECT day_type, COUNT(*) AS recorded_days,
                   SUM(total_cents) / 100.0 AS total_eur,
                   ROUND(AVG(total_cents) / 100.0, 2) AS average_eur
            FROM spending
            GROUP BY day_type
            ORDER BY day_type
        """, connection)
    finally:
        connection.close()


def weekly_summary(frame):
    if frame.empty:
        return pd.DataFrame(columns=["week_start", "recorded_days", "total_eur", "average_eur", "complete_week"])
    data = frame.copy()
    data["week_start"] = data["date"] - pd.to_timedelta(data["date"].dt.dayofweek, unit="D")
    result = data.groupby("week_start").agg(
        recorded_days=("date", "count"), total_cents=("total_cents", "sum")
    ).reset_index()
    result["total_eur"] = result["total_cents"] / 100
    result["average_eur"] = (result["total_eur"] / result["recorded_days"]).round(2)
    result["complete_week"] = result["recorded_days"] == 7
    return result.drop(columns="total_cents")


def csv_values(record):
    return [datetime.strptime(record["date"], "%Y-%m-%d").strftime("%d-%m-%Y"),
            money_text(record["food_cents"]), money_text(record["transport_cents"]),
            money_text(record["other_cents"]), money_text(record["total_cents"]),
            record["day_type"], record["data_source"]]


def write_records(records, csv_file):
    csv_file = Path(csv_file)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="",
                                         dir=csv_file.parent, delete=False) as file:
            temporary = Path(file.name)
            writer = csv.writer(file, lineterminator="\n")
            writer.writerow(HEADERS)
            for record in sorted(records, key=lambda record: record["date"]):
                writer.writerow(csv_values(record))
        temporary.replace(csv_file)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def add_record(row, csv_file=CSV_FILE, db_file=DB_FILE):
    old_records = read_records(csv_file)
    new_record = validate_record(row)
    if any(record["date"] == new_record["date"] for record in old_records):
        raise ValueError("That date is already recorded. The existing row was kept.")
    write_records(old_records + [new_record], csv_file)
    try:
        reload_database(csv_file, db_file)
    except (sqlite3.Error, OSError, ValueError):
        write_records(old_records, csv_file)
        raise


def export_reports(frame, db_file=DB_FILE, folder=None):
    folder = Path(folder) if folder else ROOT / "reports"
    folder.mkdir(parents=True, exist_ok=True)
    category_summary(frame).to_csv(folder / "category_totals.csv", index=False, float_format="%.2f")
    day_type_summary(db_file).to_csv(folder / "weekday_weekend.csv", index=False, float_format="%.2f")
    weekly_summary(frame).to_csv(folder / "weekly_summary.csv", index=False,
                                 date_format="%d-%m-%Y", float_format="%.2f")
    days, cents, average, first, last = database_summary(db_file)
    sources = frame["data_source"].value_counts().to_dict()
    lines = ["PERSONAL SPENDING TRACKER", "", "Data sources: " + str(sources),
             f"Days in database: {days}", f"Total spending: EUR {money_text(cents)}",
             f"Average per recorded day: EUR {(average or 0) / 100:.2f}",
             f"Date range: {first or 'none'} to {last or 'none'}", "",
             "CATEGORY TOTALS", category_summary(frame).to_string(index=False), "",
             "WEEKDAY AND WEEKEND COMPARISON", day_type_summary(db_file).to_string(index=False), "",
             "WEEKLY TOTALS", weekly_summary(frame).to_string(index=False), "",
             "Simulated rows are invented examples, not measured personal spending.",
             "Averages use recorded days. Missing dates are not treated as zero.",
             "A complete week contains seven recorded days."]
    (folder / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return folder
