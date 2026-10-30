-- MiniPay application extension tables
CREATE TABLE IF NOT EXISTS idempotency_keys (
  key            VARCHAR(100) PRIMARY KEY,
  request_hash   CHAR(64)     NOT NULL,
  transaction_id BIGINT       NULL REFERENCES transactions(id),
  created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
