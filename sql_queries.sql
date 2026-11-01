-- The database stores amounts in cents. Divide by 100.0 for euro amounts.

SELECT date, total_cents / 100.0 AS total_eur, day_type, data_source
FROM spending
ORDER BY date;

SELECT COUNT(*) AS recorded_days,
       SUM(total_cents) / 100.0 AS total_eur,
       ROUND(AVG(total_cents) / 100.0, 2) AS average_eur
FROM spending;

SELECT day_type, COUNT(*) AS recorded_days,
       SUM(total_cents) / 100.0 AS total_eur,
       ROUND(AVG(total_cents) / 100.0, 2) AS average_eur
FROM spending
GROUP BY day_type
ORDER BY day_type;

SELECT date, total_cents / 100.0 AS total_eur
FROM spending
ORDER BY total_cents DESC, date
LIMIT 5;

-- Filter a date range. SQLite dates are stored as YYYY-MM-DD.
SELECT * FROM spending
WHERE date BETWEEN '2026-10-01' AND '2026-10-15'
ORDER BY date;

SELECT data_source, COUNT(*) AS recorded_days
FROM spending
GROUP BY data_source;
