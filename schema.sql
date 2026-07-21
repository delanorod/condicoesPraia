-- Rode isto no SQL Editor do painel do Supabase.

CREATE TABLE IF NOT EXISTS beaches (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    municipality  TEXT NOT NULL DEFAULT 'Rio de Janeiro',
    neighborhood  TEXT NOT NULL DEFAULT '',
    region        TEXT NOT NULL DEFAULT '',
    latitude      DOUBLE PRECISION NOT NULL,
    longitude     DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS coastal_conditions (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    beach_id            TEXT NOT NULL REFERENCES beaches(id),
    observed_at         TIMESTAMPTZ NOT NULL,
    wind_speed_ms       DOUBLE PRECISION NOT NULL,
    wind_gust_ms        DOUBLE PRECISION NOT NULL,
    wind_direction_deg  DOUBLE PRECISION NOT NULL,
    wave_height_m       DOUBLE PRECISION NOT NULL,
    wave_period_s       DOUBLE PRECISION NOT NULL,
    wave_direction_deg  DOUBLE PRECISION NOT NULL,
    sea_state           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conditions_beach_time
    ON coastal_conditions (beach_id, observed_at DESC);

-- Balneabilidade: separada de propósito (fonte, frequência e natureza do
-- dado diferentes de vento/onda). Uma linha por praia, sempre sobrescrita
-- (upsert) com o status mais recente -- não é um histórico como
-- coastal_conditions.
CREATE TABLE IF NOT EXISTS balneability (
    beach_id     TEXT PRIMARY KEY REFERENCES beaches(id),
    status       TEXT NOT NULL,  -- 'propria' | 'impropria' | 'indisponivel'
    checked_at   TIMESTAMPTZ NOT NULL
);

-- Habilita acesso via API REST (o cliente supabase-py usa isso).
ALTER TABLE beaches ENABLE ROW LEVEL SECURITY;
ALTER TABLE coastal_conditions ENABLE ROW LEVEL SECURITY;
ALTER TABLE balneability ENABLE ROW LEVEL SECURITY;

-- Como o backend usa a service_role key, ela já ignora RLS (acesso total).
-- Estas policies só importam se algum dia você expuser a anon key
-- diretamente para o app mobile ler sem passar pela sua API.
CREATE POLICY "Leitura pública de praias" ON beaches
    FOR SELECT USING (true);
CREATE POLICY "Leitura pública de condições" ON coastal_conditions
    FOR SELECT USING (true);
CREATE POLICY "Leitura pública de balneabilidade" ON balneability
    FOR SELECT USING (true);
