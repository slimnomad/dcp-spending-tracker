# Spending Data Dictionary

The included dataset has 31 simulated daily records for October 2026. Amounts, dates, and spending patterns are generated examples rather than personal measurements. The `data_source` column preserves that distinction in every CSV and database row.

## Variables

| Column | Type | Unit or values | Definition |
| --- | --- | --- | --- |
| `date` | Date | DD-MM-YYYY | One calendar day, appearing once in the CSV. |
| `food_drink_eur` | Decimal | EUR, zero or more | Food, groceries, meals, snacks, and drinks. |
| `transport_eur` | Decimal | EUR, zero or more | Transport spending. |
| `other_eur` | Decimal | EUR, zero or more | Spending outside the other two categories. |
| `total_eur` | Decimal | EUR, zero or more | Sum of the three category amounts. |
| `day_type` | Category | Weekday or Weekend | Monday–Friday is Weekday; Saturday–Sunday is Weekend. |
| `data_source` | Category | Simulated or Recorded | Simulated is generated data. Recorded is a manually recorded observation. |

## Record rules

- One row represents one day, and every row contains all seven fields.
- Dates use a year from 1900 to 2100, within the range supported by the application's date analysis.
- Amounts use a decimal point, at most two decimal places, and no currency symbols.
- Each expense belongs to exactly one category.
- The total must match the sum of the three category amounts.
- A zero is a genuine zero amount within the stated data source. A missing date is not converted to a zero.
- The day type must agree with the calendar date.
- The included records are all marked Simulated. The application asks for the source when adding another row.

## Database storage

The SQLite table is named `spending`. It contains `date`, `food_cents`, `transport_cents`, `other_cents`, `total_cents`, `day_type`, and `data_source`.

Dates are stored as ISO dates (YYYY-MM-DD) so SQL sorting and date-range comparisons work. Amounts are stored as whole cents: EUR 7.50 becomes 750. The date is the primary key. SQLite constraints reject negative amounts, invalid source/day-type labels, and inconsistent totals.

The complete CSV is validated before an import changes the database. Re-importing replaces the database's derived rows in a transaction rather than appending duplicate dates. Values and their combined total must fit SQLite's signed 64-bit integer storage.

## Analysis definitions

- Daily average = total spending divided by the number of daily records present.
- Category share = category spending divided by all spending, multiplied by 100.
- Weekday/weekend averages are calculated separately, with each group's number of records shown.
- Weeks start on Monday. Weekly totals include only dates present in the dataset.
- A complete calendar week has seven daily records. Partial weeks are labelled and shown in grey in the chart.
- No analysis result should be interpreted as a conclusion about real personal spending when its source rows are Simulated.
