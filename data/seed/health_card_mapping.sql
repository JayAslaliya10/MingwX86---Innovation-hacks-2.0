-- Seed data: static health card number → payer + policy type mapping
-- In production this would be a much larger dataset

INSERT INTO payers (id, name, bulletin_url, policy_index_url) VALUES
  ('a1000000-0000-0000-0000-000000000001', 'UnitedHealthcare',
   'https://www.uhcprovider.com/en/policies-protocols/commercial-policies/commercial-medical-drug-policies.html',
   'https://www.uhcprovider.com/en/policies-protocols/commercial-policies/commercial-medical-drug-policies.html'),
  ('a2000000-0000-0000-0000-000000000002', 'Cigna',
   'https://static.cigna.com/assets/chcp/resourceLibrary/coveragePolicies/pharmacy_a-z.html',
   'https://static.cigna.com/assets/chcp/resourceLibrary/coveragePolicies/pharmacy_a-z.html'),
  ('a3000000-0000-0000-0000-000000000003', 'Aetna',
   'https://www.aetna.com/health-care-professionals/clinical-policy-bulletins/medical-clinical-policy-bulletins.html',
   'https://www.aetna.com/health-care-professionals/clinical-policy-bulletins/medical-clinical-policy-bulletins.html')
ON CONFLICT DO NOTHING;

-- Sample health card mappings (UHC)
INSERT INTO health_card_policy_map (id, health_card_number, payer_name, policy_type, policy_ids) VALUES
  (gen_random_uuid(), 'UHC-1001-2024', 'UnitedHealthcare', 'Commercial Medical Drug Policy', '{}'),
  (gen_random_uuid(), 'UHC-1002-2024', 'UnitedHealthcare', 'Commercial Medical Drug Policy', '{}'),
  (gen_random_uuid(), 'UHC-1003-2024', 'UnitedHealthcare', 'Commercial Medical Drug Policy', '{}'),
  (gen_random_uuid(), 'UHC-2001-2024', 'UnitedHealthcare', 'Medicare Advantage Drug Policy', '{}'),
  (gen_random_uuid(), 'UHC-2002-2024', 'UnitedHealthcare', 'Medicare Advantage Drug Policy', '{}');

-- Sample health card mappings (Cigna)
INSERT INTO health_card_policy_map (id, health_card_number, payer_name, policy_type, policy_ids) VALUES
  (gen_random_uuid(), 'CIGNA-3001-2024', 'Cigna', 'Drug and Biologic Coverage Policy', '{}'),
  (gen_random_uuid(), 'CIGNA-3002-2024', 'Cigna', 'Drug and Biologic Coverage Policy', '{}'),
  (gen_random_uuid(), 'CIGNA-3003-2024', 'Cigna', 'Drug and Biologic Coverage Policy', '{}');

-- Sample health card mappings (Aetna)
INSERT INTO health_card_policy_map (id, health_card_number, payer_name, policy_type, policy_ids) VALUES
  (gen_random_uuid(), 'AETNA-4001-2024', 'Aetna', 'Clinical Policy Bulletin', '{}'),
  (gen_random_uuid(), 'AETNA-4002-2024', 'Aetna', 'Clinical Policy Bulletin', '{}'),
  (gen_random_uuid(), 'AETNA-4003-2024', 'Aetna', 'Clinical Policy Bulletin', '{}');
