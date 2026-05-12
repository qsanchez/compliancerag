SELECT
    country,
    COUNT(*)                 AS num_fines,
    SUM(fine_amount_eur)     AS total_eur,
    AVG(fine_amount_eur)     AS avg_eur,
    MAX(fine_amount_eur)     AS max_eur
FROM gdpr_fines
WHERE fine_amount_eur > 0
GROUP BY country
ORDER BY total_eur DESC
LIMIT 20
