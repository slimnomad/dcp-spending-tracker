import sqlite3
import sys

try:
    from tracker import (ROOT, reload_database, load_frame,
                         parse_date, money_to_cents, money_text, add_record,
                         database_summary, category_summary, day_type_summary,
                         weekly_summary, export_reports)
except ImportError:
    print("Install the project dependencies first: python -m pip install -r requirements.txt")
    raise SystemExit(1)


def show_records(frame):
    if frame.empty:
        print("No records found.")
        return
    display = frame[["date", "food_drink_eur", "transport_eur", "other_eur",
                     "total_eur", "day_type", "data_source"]].copy()
    display["date"] = display["date"].dt.strftime("%d-%m-%Y")
    print(display.to_string(index=False, float_format=lambda amount: f"{amount:.2f}"))


def show_summary(frame):
    days, total, average, first, last = database_summary()
    print(f"\nRecorded days: {days}")
    print(f"Total spending: EUR {money_text(total)}")
    print(f"Average per recorded day: EUR {(average or 0) / 100:.2f}")
    if days:
        print(f"Date range: {first} to {last}")
        biggest = frame.loc[frame["total_cents"].idxmax()]
        print(f"Highest spending day: {biggest['date']:%d-%m-%Y}, EUR {biggest['total_eur']:.2f}")
    print("\n" + category_summary(frame).to_string(index=False, float_format=lambda amount: f"{amount:.2f}"))


def find_records():
    start = parse_date(input("Start date (DD-MM-YYYY): "))
    end_text = input("End date (Enter for the same day): ").strip()
    end = parse_date(end_text) if end_text else start
    if end < start:
        raise ValueError("The end date cannot be before the start date.")
    show_records(load_frame(start=start.isoformat(), end=end.isoformat()))


def enter_day():
    date_text = input("Date (DD-MM-YYYY): ").strip()
    day = parse_date(date_text)
    food = input("Food and drinks (EUR): ").strip()
    transport = input("Transport (EUR): ").strip()
    other = input("Other spending (EUR): ").strip()
    total = money_to_cents(food) + money_to_cents(transport) + money_to_cents(other)
    source = input("Data source: 1 = Recorded, 2 = Simulated: ").strip()
    if source not in ("1", "2"):
        raise ValueError("Choose 1 or 2 for the data source.")
    row = {"date": date_text, "food_drink_eur": food,
           "transport_eur": transport, "other_eur": other,
           "total_eur": money_text(total),
           "day_type": "Weekend" if day.weekday() >= 5 else "Weekday",
           "data_source": "Recorded" if source == "1" else "Simulated"}
    add_record(row)
    print(f"Saved {date_text}. Total: EUR {money_text(total)}")


def main():
    try:
        count = reload_database()
        print(f"Loaded {count} daily records into SQLite.")
        while True:
            frame = load_frame()
            print("\n===== PERSONAL SPENDING TRACKER =====")
            sources = frame["data_source"].value_counts().to_dict()
            print("Data sources: " + str(sources))
            print("1. View all records")
            print("2. Find a day or date range")
            print("3. Total spending and category comparison")
            print("4. Compare weekdays and weekends")
            print("5. Weekly summary")
            print("6. Generate charts")
            print("7. Add a daily record")
            print("8. Export analysis reports")
            print("0. Exit")
            choice = input("Choose an option: ").strip()
            try:
                if choice == "1":
                    show_records(frame)
                elif choice == "2":
                    find_records()
                elif choice == "3":
                    show_summary(frame)
                elif choice == "4":
                    comparison = day_type_summary()
                    print(comparison.to_string(index=False, float_format=lambda amount: f"{amount:.2f}"))
                    print("Averages compare recorded days, including recorded zero-spending days.")
                elif choice == "5":
                    weekly = weekly_summary(frame)
                    if weekly.empty:
                        print("No records found.")
                    else:
                        weekly["week_start"] = weekly["week_start"].dt.strftime("%d-%m-%Y")
                        print(weekly.to_string(index=False, float_format=lambda amount: f"{amount:.2f}"))
                        print("Complete week = seven recorded days. Missing dates are not zeros.")
                elif choice == "6":
                    from charts import generate_charts
                    for path in generate_charts(frame):
                        print("Saved " + str(path.relative_to(ROOT)))
                elif choice == "7":
                    enter_day()
                elif choice == "8":
                    folder = export_reports(frame)
                    print("Saved reports to " + str(folder))
                elif choice == "0":
                    print("Goodbye.")
                    return 0
                else:
                    print("Invalid choice. Select 0 to 8.")
            except ImportError:
                print("Install the chart dependency: python -m pip install -r requirements.txt")
            except (ValueError, OSError, sqlite3.Error) as error:
                print(f"Could not complete that option: {error}")
    except (ValueError, OSError, sqlite3.Error) as error:
        print(f"Could not load the project: {error}")
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nSession ended.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
