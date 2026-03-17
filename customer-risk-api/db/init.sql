CREATE TABLE IF NOT EXISTS customers (
    customer_id  VARCHAR(20) PRIMARY KEY,
    risk_tier    TEXT        NOT NULL CHECK (risk_tier IN ('LOW', 'MEDIUM', 'HIGH')),
    risk_factors TEXT[]      NOT NULL
);

INSERT INTO customers (customer_id, risk_tier, risk_factors) VALUES
    ('CUST-001', 'LOW', ARRAY['stable_income']),
    ('CUST-002', 'LOW', ARRAY['long_account_tenure', 'no_missed_payments']),
    ('CUST-003', 'LOW', ARRAY['stable_income', 'low_credit_utilisation', 'no_missed_payments']),
    ('CUST-004', 'LOW', ARRAY['long_account_tenure', 'consistent_repayment_history']),
    ('CUST-005', 'LOW', ARRAY['stable_income', 'no_missed_payments']),

    ('CUST-006', 'MEDIUM', ARRAY['recent_address_change', 'moderate_credit_utilisation']),
    ('CUST-007', 'MEDIUM', ARRAY['occasional_late_payment', 'short_account_tenure']),
    ('CUST-008', 'MEDIUM', ARRAY['moderate_credit_utilisation', 'recent_address_change', 'new_credit_account']),
    ('CUST-009', 'MEDIUM', ARRAY['occasional_late_payment', 'moderate_credit_utilisation']),
    ('CUST-010', 'MEDIUM', ARRAY['recent_employer_change', 'short_account_tenure', 'moderate_credit_utilisation']),

    ('CUST-011', 'HIGH', ARRAY['multiple_missed_payments', 'high_credit_utilisation']),
    ('CUST-012', 'HIGH', ARRAY['sanctions_watchlist_match', 'identity_verification_failed', 'multiple_missed_payments']),
    ('CUST-013', 'HIGH', ARRAY['high_transaction_volume', 'multiple_missed_payments', 'recent_default', 'account_under_review']),
    ('CUST-014', 'HIGH', ARRAY['identity_verification_failed', 'high_transaction_volume', 'sanctions_watchlist_match']),
    ('CUST-015', 'HIGH', ARRAY['multiple_missed_payments', 'high_credit_utilisation', 'recent_default']);
