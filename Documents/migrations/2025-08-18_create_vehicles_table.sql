-- Migration: create vehicles table
-- Adds a vehicles table linked to customers to store multiple vehicles per customer

CREATE TABLE IF NOT EXISTS vehicles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    make VARCHAR(128) DEFAULT NULL,
    model VARCHAR(128) DEFAULT NULL,
    year SMALLINT DEFAULT NULL,
    vin VARCHAR(64) DEFAULT NULL,
    license_plate VARCHAR(32) DEFAULT NULL,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_vehicles_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Add vehicle_id column to work_orders and appointments
ALTER TABLE work_orders
    ADD COLUMN IF NOT EXISTS vehicle_id INT DEFAULT NULL;

ALTER TABLE appointments
    ADD COLUMN IF NOT EXISTS vehicle_id INT DEFAULT NULL;

-- Add foreign keys
ALTER TABLE work_orders
    ADD CONSTRAINT IF NOT EXISTS fk_work_orders_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL;

ALTER TABLE appointments
    ADD CONSTRAINT IF NOT EXISTS fk_appointments_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL;
