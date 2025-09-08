# Guide de Reproduction - ChronoTech Tests

## Prérequis
```bash
cd /home/amenard/Chronotech/ChronoTech
source venv/bin/activate
export MYSQL_HOST=192.168.50.101
export MYSQL_USER=gsicloud
export MYSQL_PASSWORD='TCOChoosenOne204$'
export MYSQL_DATABASE=bdm
```

## Lancer les tests CRUD
```bash
python3 seeds/chronotech_crud_tester.py
```

## Vérifier les résultats
```bash
cat seeds/smoke_crud_report.json
cat seeds/data_coverage.json
cat seeds/missing_features.md
```

## Peupler la base avec des données de test
```bash
python3 seeds/chronotech_data_seeder.py
```
