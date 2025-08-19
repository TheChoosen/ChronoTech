-- Migration: add index on vehicles(customer_id)
-- Safe reference SQL: apply via migration runner or DBA tool
ALTER TABLE vehicles
  ADD INDEX idx_vehicles_customer_id (customer_id);
