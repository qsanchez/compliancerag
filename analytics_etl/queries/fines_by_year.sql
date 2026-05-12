SELECT
    year(decision_date)      AS year,
    COUNT(*)                 AS num_fines,
    SUM(fine_amount_eur)     AS total_eur,
    AVG(fine_amount_eur)     AS avg_eur,
    MAX(fine_amount_eur)     AS max_eur
FROM gdpr_fines
WHERE fine_amount_eur > 0
GROUP BY year(decision_date)
ORDER BY year ASC
