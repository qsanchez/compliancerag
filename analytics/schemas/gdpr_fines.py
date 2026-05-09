import pyarrow as pa

SCHEMA = pa.schema([
    pa.field("decision_date", pa.date32()),
    pa.field("country", pa.string()),
    pa.field("authority", pa.string()),
    pa.field("fine_amount_eur", pa.int64()),
    pa.field("controller", pa.string()),
    pa.field("sector", pa.string()),
    pa.field("articles_violated", pa.string()),
    pa.field("violation_type", pa.string()),
    pa.field("summary", pa.string()),
])
