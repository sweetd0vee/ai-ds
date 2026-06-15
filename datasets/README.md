# Датасеты

Тестовые таблицы для «Электронного Data Scientist». В каждом файле заложены **известные зависимости** — удобно проверять, находит ли система закономерности.

## Сводная таблица

| Файл | Строк | Столбцов | Домен | Размер |
|------|------:|---------:|-------|--------|
| `marketing_roi_20x60.csv` | 60 | 20 | Маркетинг / ROI рекламы | малый |
| `sample_30x100.csv` | 100 | 30 | E-commerce (заказы) | малый |
| `realestate_prices_16x150.csv` | 150 | 18 | Недвижимость / цены | малый |
| `manufacturing_quality_28x300.csv` | 300 | 31 | Производство / брак | средний |
| `healthcare_visits_24x400.csv` | 400 | 26 | Медицина / стоимость лечения | средний |
| `hr_attrition_35x500.csv` | 500 | 36 | HR / текучесть кадров | средний |
| `bank_churn_22x800.csv` | 800 | 21 | Банк / отток клиентов | средний+ |
| `ecommerce_orders_22x1200.csv` | 1200 | 27 | E-commerce (крупнее) | большой |
| `iot_energy_12x2000.csv` | 2000 | 13 | IoT / энергопотребление | большой |

## Ключевые зависимости (ground truth)

### `marketing_roi_20x60.csv`
- `ad_spend` → `conversions`, `revenue`
- `channel` (email > search > social > display) влияет на `conversion_rate`
- `season` влияет на эффективность кампаний
- `roi_pct` = f(revenue, ad_spend)

### `sample_30x100.csv`
- `revenue` ≈ `quantity × unit_price × (1 - discount)`
- `margin` = `revenue - cost`
- `customer_segment`, `region`, `channel` влияют на метрики

### `realestate_prices_16x150.csv`
- `price_k_rub` ~ `area_sqm × район + rooms + renovation - building_age - metro_distance`
- Район `center` дороже `suburb`
- `price_per_sqm` производный от цены и площади

### `manufacturing_quality_28x300.csv`
- `defect_rate` ↑ при отклонении `temperature_c` от 22°C и `humidity_pct` от 50%
- Ночная `shift` и низкий `operator_experience_years` → больше брака
- `material_grade` C хуже A/B
- `energy_kwh`, `scrap_cost_usd` связаны с объёмом и браком

### `healthcare_visits_24x400.csv`
- `treatment_cost_rub` ~ `length_of_stay_days` + диагноз + BMI + курение
- `diagnosis_category=oncology` — самые дорогие визиты
- `readmitted_30d` чаще у курящих с высоким BMI

### `hr_attrition_35x500.csv`
- `left_company` / `attrition` ↑ при высоких `overtime_hours_month`, низкой `satisfaction_score`
- `monthly_income` и `promotions_last_5y` снижают риск ухода
- `department=Sales` — выше текучесть

### `bank_churn_22x800.csv`
- `exited` ↑ при `num_products=1`, низком `credit_score`, `is_active_member=False`
- `geography`, `tenure_years`, `balance` влияют на отток

### `ecommerce_orders_22x1200.csv`
- `revenue`, `margin`, `nps` связаны с сегментом, скидкой, каналом
- `is_returned` ↑ при больших `discount_pct`

### `iot_energy_12x2000.csv`
- `energy_kwh` зависит от `hour`, `day_of_week`, `outdoor_temp_c`
- Вечерний пик, выходные — ниже нагрузка
- ~2% строк — аномалии (`is_anomaly=True`)

## Регенерация

```powershell
cd C:\Users\audit\Work\Arina\2026\ai-ds\new\backend
.\venv\Scripts\Activate.ps1
python ..\..\datasets\generate_datasets.py
```

Скрипт перезапишет все синтетические CSV (кроме `sample_30x100.csv` — он исходный).

## Использование

Перетащите любой `.csv` на http://localhost:5173

Рекомендуемый порядок тестов:
1. `marketing_roi_20x60.csv` — быстрый прогон (~1–2 мин)
2. `hr_attrition_35x500.csv` — категории + бинарный таргет
3. `iot_energy_12x2000.csv` — временные ряды, много строк
4. `ecommerce_orders_22x1200.csv` — полный пайплайн на объёме
