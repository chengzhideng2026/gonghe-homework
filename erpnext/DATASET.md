# DATASET — Crestwind Compressor (Ground Truth)

Every value below is deterministic: recreate the stack with
`docker compose down -v && docker compose up -d` and you get the same numbers.
Tables are rendered from the restored site through the REST API.

> **Date pin — read this before reasoning about anything time-relative.**
> The pinned "today" for relative date questions is **2025-10-15**. Every
> record's posting date is in 2025, but agents that anchor to the host's
> system clock will see today as 2026 or later. ERPNext's own `status`
> fields are computed on the host clock: it marks three not-yet-due invoices
> as Overdue. "Overdue" means `due_date < 2025-10-15 and outstanding > 0`.

## Company

- **Name:** Crestwind Compressor Manufacturing Co. (abbreviation **CCM**)
- **Currency:** USD. **Country:** United States. **Fiscal year:** 2025-01-01 to 2025-12-31.
- **Warehouses:** raw materials and sub-assemblies in `Stores - CCM`, material
  in production in `Work In Progress - CCM`, compressors in `Finished Goods - CCM`.
- **Login:** Administrator / admin. **API key pair:** `crestwind-agent` / `crestwind-agent-secret`.

## Items

### Raw Materials (purchased) (12)

| Item Code | Item Name | Valuation | UOM |
|---|---|---:|---|
| RM-BRG-NSK-6203 | NSK Bearing 6203 | 4.2 | Nos |
| RM-CAP-RUN-25 | Run Capacitor 25uF | 3.3 | Nos |
| RM-COIL-CU-2.0 | Copper Coil 2.0mm | 28.5 | Meter |
| RM-CONN-TERM-3P | 3-Pin Terminal Connector | 0.85 | Nos |
| RM-DISCH-PIPE-CU | Copper Discharge Pipe | 5.4 | Nos |
| RM-LAM-SI-035 | Silicon Steel Lamination 0.35mm | 3.8 | Nos |
| RM-OIL-POE-1L | POE Refrigerant Oil 1L | 6.75 | Litre |
| RM-PIST-AL-22 | Aluminum Piston 22mm | 7.1 | Nos |
| RM-SHELL-STEEL-A1 | Steel Shell A1 (R12) | 18 | Nos |
| RM-SHELL-STEEL-A2 | Steel Shell A2 (R32) | 19.5 | Nos |
| RM-VALVE-REED-S | Reed Valve Set | 2.4 | Nos |
| RM-WIRE-MAGNET-1.2 | Magnet Wire 1.2mm | 1.95 | Meter |

### Sub Assemblies (manufactured) (3)

| Item Code | Item Name | Valuation | UOM |
|---|---|---:|---|
| SA-MOTOR-1HP | Motor Assembly 1HP | 525.35 | Nos |
| SA-PUMP-R12 | Pump Mechanism R12 | 39.65 | Nos |
| SA-PUMP-R32 | Pump Mechanism R32 | 41.15 | Nos |

### Finished Goods (sold) (3)

| Item Code | Item Name | Valuation | UOM |
|---|---|---:|---|
| FG-COMP-1.5HP-R32 | Rotary Compressor 1.5HP R32 220V | 632.2 | Nos |
| FG-COMP-1HP-R32 | Rotary Compressor 1HP R32 220V | 575.2 | Nos |
| FG-COMP-2HP-R12 | Rotary Compressor 2HP R12 220V | 573.7 | Nos |

## Bill of Materials

| BOM | Produces | Total Cost |
|---|---|---:|
| BOM-FG-COMP-1.5HP-R32-001 | FG-COMP-1.5HP-R32 | 632.2 |
| BOM-FG-COMP-1HP-R32-001 | FG-COMP-1HP-R32 | 575.2 |
| BOM-FG-COMP-2HP-R12-001 | FG-COMP-2HP-R12 | 573.7 |
| BOM-SA-MOTOR-1HP-001 | SA-MOTOR-1HP | 525.35 |
| BOM-SA-PUMP-R12-001 | SA-PUMP-R12 | 39.65 |
| BOM-SA-PUMP-R32-001 | SA-PUMP-R32 | 41.15 |

Valuation of manufactured items equals their BOM cost at the raw-material valuation
rates. The stock ledger carries actual cost, which is lower where copper was bought
below its valuation rate: SA-MOTOR-1HP 519.57, SA-PUMP-R32 40.43, FG-COMP-1HP-R32 566.81
(moving average as of 2025-10-15). The Standard Selling price list has FG-COMP-1HP-R32
at 600, FG-COMP-1.5HP-R32 at 720, FG-COMP-2HP-R12 at 850.

Components per unit produced:

- **FG-COMP-1.5HP-R32:** 1 SA-MOTOR-1HP + 1 SA-PUMP-R32 + 1 RM-CAP-RUN-25 + 1 RM-DISCH-PIPE-CU + 2 RM-COIL-CU-2.0
- **FG-COMP-1HP-R32:** 1 SA-MOTOR-1HP + 1 SA-PUMP-R32 + 1 RM-CAP-RUN-25 + 1 RM-DISCH-PIPE-CU
- **FG-COMP-2HP-R12:** 1 SA-MOTOR-1HP + 1 SA-PUMP-R12 + 1 RM-CAP-RUN-25 + 1 RM-DISCH-PIPE-CU
- **SA-MOTOR-1HP:** 5 RM-COIL-CU-2.0 + 80 RM-LAM-SI-035 + 40 RM-WIRE-MAGNET-1.2 + 1 RM-CONN-TERM-3P
- **SA-PUMP-R12:** 2 RM-BRG-NSK-6203 + 1 RM-PIST-AL-22 + 2 RM-VALVE-REED-S + 1 RM-SHELL-STEEL-A1 + 0.2 RM-OIL-POE-1L
- **SA-PUMP-R32:** 2 RM-BRG-NSK-6203 + 1 RM-PIST-AL-22 + 2 RM-VALVE-REED-S + 1 RM-SHELL-STEEL-A2 + 0.2 RM-OIL-POE-1L

## Stock state

| Warehouse | Item | On hand | Reserved (SO) | Reserved (WO) | On order (PO) | Planned (WO) | Projected |
|---|---|---:|---:|---:|---:|---:|---:|
| Finished Goods - CCM | FG-COMP-1.5HP-R32 | 0 | 25 | 0 | 0 | 30 | 5 |
| Finished Goods - CCM | FG-COMP-1HP-R32 | 9 | 12 | 0 | 0 | 0 | -3 |
| Finished Goods - CCM | FG-COMP-2HP-R12 | 0 | 8 | 0 | 0 | 0 | -8 |
| Stores - CCM | RM-BRG-NSK-6203 | 130 | 0 | 0 | 100 | 0 | 230 |
| Stores - CCM | RM-CAP-RUN-25 | 205 | 0 | 30 | 50 | 0 | 225 |
| Stores - CCM | RM-COIL-CU-2.0 | 50 | 0 | 60 | 200 | 0 | 190 |
| Stores - CCM | RM-CONN-TERM-3P | 75 | 0 | 0 | 0 | 0 | 75 |
| Stores - CCM | RM-DISCH-PIPE-CU | 185 | 0 | 30 | 50 | 0 | 205 |
| Stores - CCM | RM-LAM-SI-035 | 3000 | 0 | 0 | 2000 | 0 | 5000 |
| Stores - CCM | RM-OIL-POE-1L | 53 | 0 | 0 | 20 | 0 | 73 |
| Stores - CCM | RM-PIST-AL-22 | 125 | 0 | 0 | 0 | 0 | 125 |
| Stores - CCM | RM-SHELL-STEEL-A1 | 40 | 0 | 0 | 0 | 0 | 40 |
| Stores - CCM | RM-SHELL-STEEL-A2 | 65 | 0 | 0 | 30 | 0 | 95 |
| Stores - CCM | RM-VALVE-REED-S | 30 | 0 | 0 | 0 | 0 | 30 |
| Stores - CCM | RM-WIRE-MAGNET-1.2 | 2500 | 0 | 0 | 0 | 0 | 2500 |
| Stores - CCM | SA-MOTOR-1HP | 20 | 0 | 30 | 0 | 0 | -10 |
| Stores - CCM | SA-PUMP-R12 | 0 | 0 | 0 | 0 | 10 | 10 |
| Stores - CCM | SA-PUMP-R32 | 20 | 0 | 30 | 0 | 0 | -10 |
| Work In Progress - CCM | RM-BRG-NSK-6203 | 20 | 0 | 0 | 0 | 0 | 20 |
| Work In Progress - CCM | RM-OIL-POE-1L | 2 | 0 | 0 | 0 | 0 | 2 |
| Work In Progress - CCM | RM-PIST-AL-22 | 10 | 0 | 0 | 0 | 0 | 10 |
| Work In Progress - CCM | RM-SHELL-STEEL-A1 | 10 | 0 | 0 | 0 | 0 | 10 |
| Work In Progress - CCM | RM-VALVE-REED-S | 20 | 0 | 0 | 0 | 0 | 20 |

## Customers and Suppliers

**Customers:** BlueRidge Cooling Systems, Cascade Thermal Systems, GreenAir HVAC Solutions, Helio Comfort Appliances, Meridian HVAC Group, Nordic Air Industries, Polaris Climate Tech, Summit Climate OEM.

**Suppliers:** Foshan Capacitor Works, Hangzhou Precision Bearings, Ningbo Copper Tube Co., Suzhou Lamination Industries, Tongling Magnet Wire Co., Yantai Refrigerant Solutions.

## Purchase Orders

| # | Date | Supplier | Lines | Total | Status |
|---|---|---|---|---:|---|
| PUR-ORD-2026-00001 | 2025-01-08 | Tongling Magnet Wire Co. | 300 RM-COIL-CU-2.0 @ 28; 2000 RM-WIRE-MAGNET-1.2 @ 1.9 | 12,200 | Completed |
| PUR-ORD-2026-00002 | 2025-01-15 | Foshan Capacitor Works | 100 RM-CAP-RUN-25 @ 3.2 | 320 | Completed |
| PUR-ORD-2026-00003 | 2025-01-22 | Suzhou Lamination Industries | 4000 RM-LAM-SI-035 @ 3.7 | 14,800 | Completed |
| PUR-ORD-2026-00004 | 2025-02-03 | Hangzhou Precision Bearings | 200 RM-BRG-NSK-6203 @ 4.1; 100 RM-PIST-AL-22 @ 7 | 1,520 | Completed |
| PUR-ORD-2026-00005 | 2025-02-12 | Ningbo Copper Tube Co. | 100 RM-DISCH-PIPE-CU @ 5.3 | 530 | Completed |
| PUR-ORD-2026-00006 | 2025-02-20 | Yantai Refrigerant Solutions | 40 RM-OIL-POE-1L @ 6.8 | 272 | Completed |
| PUR-ORD-2026-00007 | 2025-03-05 | Tongling Magnet Wire Co. | 200 RM-COIL-CU-2.0 @ 28.2 | 5,640 | Completed |
| PUR-ORD-2026-00008 | 2025-03-18 | Hangzhou Precision Bearings | 60 RM-SHELL-STEEL-A2 @ 19; 200 RM-VALVE-REED-S @ 2.35 | 1,610 | Completed |
| PUR-ORD-2026-00009 | 2025-04-02 | Foshan Capacitor Works | 100 RM-CONN-TERM-3P @ 0.85; 60 RM-CAP-RUN-25 @ 3.25 | 280 | Completed |
| PUR-ORD-2026-00010 | 2025-04-14 | Suzhou Lamination Industries | 4000 RM-LAM-SI-035 @ 3.75 | 15,000 | Completed |
| PUR-ORD-2026-00011 | 2025-04-28 | Hangzhou Precision Bearings | 20 RM-SHELL-STEEL-A1 @ 18 | 360 | Completed |
| PUR-ORD-2026-00012 | 2025-05-06 | Tongling Magnet Wire Co. | 200 RM-COIL-CU-2.0 @ 28.5; 2000 RM-WIRE-MAGNET-1.2 @ 1.92 | 9,540 | Completed |
| PUR-ORD-2026-00013 | 2025-05-19 | Ningbo Copper Tube Co. | 100 RM-DISCH-PIPE-CU @ 5.35 | 535 | Completed |
| PUR-ORD-2026-00014 | 2025-06-03 | Hangzhou Precision Bearings | 200 RM-BRG-NSK-6203 @ 4.15; 60 RM-PIST-AL-22 @ 7.05 | 1,253 | Completed |
| PUR-ORD-2026-00015 | 2025-06-17 | Yantai Refrigerant Solutions | 20 RM-OIL-POE-1L @ 6.85 | 137 | Completed |
| PUR-ORD-2026-00016 | 2025-06-24 | Foshan Capacitor Works | 50 RM-CONN-TERM-3P @ 0.86 | 43 | Completed |
| PUR-ORD-2026-00017 | 2025-07-01 | Suzhou Lamination Industries | 3000 RM-LAM-SI-035 @ 3.8 | 11,400 | Completed |
| PUR-ORD-2026-00018 | 2025-07-22 | Foshan Capacitor Works | 80 RM-CAP-RUN-25 @ 3.3 | 264 | Completed |
| PUR-ORD-2026-00019 | 2025-08-05 | Hangzhou Precision Bearings | 60 RM-SHELL-STEEL-A2 @ 19.2; 100 RM-VALVE-REED-S @ 2.4 | 1,392 | Completed |
| PUR-ORD-2026-00020 | 2025-08-19 | Ningbo Copper Tube Co. | 60 RM-DISCH-PIPE-CU @ 5.4 | 324 | Completed |
| PUR-ORD-2026-00021 | 2025-09-02 | Tongling Magnet Wire Co. | 1500 RM-WIRE-MAGNET-1.2 @ 1.95 | 2,925 | Completed |
| PUR-ORD-2026-00022 | 2025-09-10 | Tongling Magnet Wire Co. | 200 RM-COIL-CU-2.0 @ 29 | 5,800 | To Receive and Bill |
| PUR-ORD-2026-00023 | 2025-09-22 | Foshan Capacitor Works | 50 RM-CAP-RUN-25 @ 3.3 | 165 | To Receive and Bill |
| PUR-ORD-2026-00024 | 2025-09-30 | Suzhou Lamination Industries | 2000 RM-LAM-SI-035 @ 3.85 | 7,700 | To Receive and Bill |
| PUR-ORD-2026-00025 | 2025-10-01 | Hangzhou Precision Bearings | 30 RM-SHELL-STEEL-A2 @ 19; 100 RM-BRG-NSK-6203 @ 4.2 | 990 | To Receive and Bill |
| PUR-ORD-2026-00026 | 2025-10-08 | Yantai Refrigerant Solutions | 20 RM-OIL-POE-1L @ 6.9 | 138 | To Receive and Bill |
| PUR-ORD-2026-00027 | 2025-10-12 | Ningbo Copper Tube Co. | 50 RM-DISCH-PIPE-CU @ 5.45 | 272.5 | To Receive and Bill |

**Open (To Receive and Bill):** 6 POs, total $15,065.5.

Every purchase order's required-by date equals its order date; this is how the data was
entered, not supplier performance. The pending Tongling copper order (PUR-ORD-2026-00022)
covers the copper shortage on MFG-WO-2026-00020.

## Sales Orders

| # | Date | Customer | Lines | Total | Status |
|---|---|---|---|---:|---|
| SAL-ORD-2026-00001 | 2025-03-10 | GreenAir HVAC Solutions | 10 FG-COMP-1HP-R32 @ 600 | 6,000 | Completed |
| SAL-ORD-2026-00002 | 2025-03-20 | BlueRidge Cooling Systems | 6 FG-COMP-1HP-R32 @ 590 | 3,540 | Completed |
| SAL-ORD-2026-00003 | 2025-04-14 | Summit Climate OEM | 5 FG-COMP-2HP-R12 @ 850 | 4,250 | Completed |
| SAL-ORD-2026-00004 | 2025-04-22 | Polaris Climate Tech | 4 FG-COMP-1HP-R32 @ 580 | 2,320 | Completed |
| SAL-ORD-2026-00005 | 2025-05-15 | GreenAir HVAC Solutions | 12 FG-COMP-1HP-R32 @ 600 | 7,200 | Completed |
| SAL-ORD-2026-00006 | 2025-05-20 | Summit Climate OEM | 2 FG-COMP-1HP-R32 @ 600 | 1,200 | Completed |
| SAL-ORD-2026-00007 | 2025-05-28 | Cascade Thermal Systems | 3 FG-COMP-2HP-R12 @ 860 | 2,580 | Completed |
| SAL-ORD-2026-00008 | 2025-06-02 | Helio Comfort Appliances | 6 FG-COMP-1HP-R32 @ 605 | 3,630 | Completed |
| SAL-ORD-2026-00009 | 2025-06-16 | Nordic Air Industries | 10 FG-COMP-1.5HP-R32 @ 720 | 7,200 | Completed |
| SAL-ORD-2026-00010 | 2025-06-30 | Meridian HVAC Group | 5 FG-COMP-1HP-R32 @ 595; 5 FG-COMP-1.5HP-R32 @ 725 | 6,600 | Completed |
| SAL-ORD-2026-00011 | 2025-07-18 | GreenAir HVAC Solutions | 10 FG-COMP-1HP-R32 @ 600 | 6,000 | Completed |
| SAL-ORD-2026-00012 | 2025-07-25 | Summit Climate OEM | 6 FG-COMP-2HP-R12 @ 850 | 5,100 | Completed |
| SAL-ORD-2026-00013 | 2025-08-01 | Polaris Climate Tech | 8 FG-COMP-1HP-R32 @ 580 | 4,640 | Completed |
| SAL-ORD-2026-00014 | 2025-08-12 | BlueRidge Cooling Systems | 4 FG-COMP-1HP-R32 @ 590 | 2,360 | Completed |
| SAL-ORD-2026-00015 | 2025-08-29 | Helio Comfort Appliances | 12 FG-COMP-1.5HP-R32 @ 720 | 8,640 | Completed |
| SAL-ORD-2026-00016 | 2025-09-03 | Cascade Thermal Systems | 4 FG-COMP-2HP-R12 @ 860 | 3,440 | Completed |
| SAL-ORD-2026-00017 | 2025-09-16 | GreenAir HVAC Solutions | 10 FG-COMP-1HP-R32 @ 610 | 6,100 | Completed |
| SAL-ORD-2026-00018 | 2025-09-18 | Nordic Air Industries | 8 FG-COMP-1.5HP-R32 @ 720 | 5,760 | Completed |
| SAL-ORD-2026-00019 | 2025-09-24 | Meridian HVAC Group | 6 FG-COMP-1HP-R32 @ 595 | 3,570 | Completed |
| SAL-ORD-2026-00020 | 2025-09-25 | Helio Comfort Appliances | 25 FG-COMP-1.5HP-R32 @ 720 | 18,000 | To Deliver and Bill |
| SAL-ORD-2026-00021 | 2025-10-02 | GreenAir HVAC Solutions | 8 FG-COMP-1HP-R32 @ 610 | 4,880 | Completed |
| SAL-ORD-2026-00022 | 2025-10-05 | Summit Climate OEM | 5 FG-COMP-2HP-R12 @ 850 | 4,250 | To Deliver and Bill |
| SAL-ORD-2026-00023 | 2025-10-07 | BlueRidge Cooling Systems | 2 FG-COMP-2HP-R12 @ 850 | 1,700 | Completed |
| SAL-ORD-2026-00024 | 2025-10-12 | Nordic Air Industries | 12 FG-COMP-1HP-R32 @ 610 | 7,320 | To Deliver and Bill |
| SAL-ORD-2026-00025 | 2025-10-13 | Cascade Thermal Systems | 3 FG-COMP-2HP-R12 @ 860 | 2,580 | To Deliver and Bill |

**Backlog (To Deliver and Bill):** 4 SOs, total $32,150.

**Sales orders by customer:** GreenAir HVAC Solutions 5 ($30,180), Summit Climate OEM 4 ($14,800), Helio Comfort Appliances 3 ($30,270), Nordic Air Industries 3 ($20,280), Cascade Thermal Systems 3 ($8,600), BlueRidge Cooling Systems 3 ($7,600), Meridian HVAC Group 2 ($10,170), Polaris Climate Tech 2 ($6,960).

## Sales Invoices and receivables

| Invoice | Customer | Posted | Due | Total | Outstanding | As of 2025-10-15 |
|---|---|---|---|---:|---:|---|
| ACC-SINV-2026-00001 | GreenAir HVAC Solutions | 2025-03-10 | 2025-04-09 | 6,000 | 0 | Paid |
| ACC-SINV-2026-00002 | BlueRidge Cooling Systems | 2025-03-20 | 2025-04-19 | 3,540 | 0 | Paid |
| ACC-SINV-2026-00003 | Summit Climate OEM | 2025-04-14 | 2025-05-14 | 4,250 | 0 | Paid |
| ACC-SINV-2026-00004 | Polaris Climate Tech | 2025-04-22 | 2025-05-22 | 2,320 | 0 | Paid |
| ACC-SINV-2026-00005 | GreenAir HVAC Solutions | 2025-05-15 | 2025-06-14 | 7,200 | 0 | Paid |
| ACC-SINV-2026-00006 | Summit Climate OEM | 2025-05-20 | 2025-06-19 | 1,200 | 0 | Paid |
| ACC-SINV-2026-00007 | Cascade Thermal Systems | 2025-05-28 | 2025-06-27 | 2,580 | 0 | Paid |
| ACC-SINV-2026-00008 | Helio Comfort Appliances | 2025-06-02 | 2025-07-02 | 3,630 | 0 | Paid |
| ACC-SINV-2026-00009 | Nordic Air Industries | 2025-06-16 | 2025-07-16 | 7,200 | 0 | Paid |
| ACC-SINV-2026-00010 | Meridian HVAC Group | 2025-06-30 | 2025-07-30 | 6,600 | 0 | Paid |
| ACC-SINV-2026-00011 | GreenAir HVAC Solutions | 2025-07-18 | 2025-08-17 | 6,000 | 6,000 | OVERDUE 59d |
| ACC-SINV-2026-00012 | Summit Climate OEM | 2025-07-25 | 2025-08-24 | 5,100 | 0 | Paid |
| ACC-SINV-2026-00013 | Polaris Climate Tech | 2025-08-01 | 2025-08-31 | 4,640 | 4,640 | OVERDUE 45d |
| ACC-SINV-2026-00014 | BlueRidge Cooling Systems | 2025-08-12 | 2025-09-11 | 2,360 | 0 | Paid |
| ACC-SINV-2026-00015 | Helio Comfort Appliances | 2025-08-29 | 2025-09-28 | 8,640 | 8,640 | OVERDUE 17d |
| ACC-SINV-2026-00016 | Cascade Thermal Systems | 2025-09-03 | 2025-10-03 | 3,440 | 0 | Paid |
| ACC-SINV-2026-00017 | GreenAir HVAC Solutions | 2025-09-16 | 2025-10-10 | 6,100 | 6,100 | OVERDUE 5d |
| ACC-SINV-2026-00018 | Nordic Air Industries | 2025-09-18 | 2025-10-18 | 5,760 | 5,760 | Unpaid |
| ACC-SINV-2026-00019 | Meridian HVAC Group | 2025-09-24 | 2025-10-24 | 3,570 | 0 | Paid |
| ACC-SINV-2026-00020 | GreenAir HVAC Solutions | 2025-10-02 | 2025-11-01 | 4,880 | 4,880 | Unpaid |
| ACC-SINV-2026-00021 | BlueRidge Cooling Systems | 2025-10-07 | 2025-11-06 | 1,700 | 1,700 | Unpaid |

**Invoiced:** $96,710. **Total AR:** $37,720.

**AR by customer:** GreenAir HVAC Solutions $16,980 (45.0%), Helio Comfort Appliances $8,640 (22.9%), Nordic Air Industries $5,760 (15.3%), Polaris Climate Tech $4,640 (12.3%), BlueRidge Cooling Systems $1,700 (4.5%).

**Overdue:** 4: ACC-SINV-2026-00011 GreenAir HVAC Solutions $6,000 due 2025-08-17; ACC-SINV-2026-00013 Polaris Climate Tech $4,640 due 2025-08-31; ACC-SINV-2026-00015 Helio Comfort Appliances $8,640 due 2025-09-28; ACC-SINV-2026-00017 GreenAir HVAC Solutions $6,100 due 2025-10-10.

## Purchase Invoices and payables

| Invoice | Supplier | Posted | Total | Outstanding |
|---|---|---|---:|---:|
| ACC-PINV-2026-00001 | Tongling Magnet Wire Co. | 2025-01-08 | 12,200 | 0 |
| ACC-PINV-2026-00002 | Foshan Capacitor Works | 2025-01-15 | 320 | 0 |
| ACC-PINV-2026-00003 | Suzhou Lamination Industries | 2025-01-22 | 14,800 | 0 |
| ACC-PINV-2026-00004 | Hangzhou Precision Bearings | 2025-02-03 | 1,520 | 1,520 |
| ACC-PINV-2026-00005 | Ningbo Copper Tube Co. | 2025-02-12 | 530 | 0 |
| ACC-PINV-2026-00006 | Yantai Refrigerant Solutions | 2025-02-20 | 272 | 0 |
| ACC-PINV-2026-00007 | Tongling Magnet Wire Co. | 2025-03-05 | 5,640 | 0 |
| ACC-PINV-2026-00008 | Hangzhou Precision Bearings | 2025-03-18 | 1,610 | 0 |
| ACC-PINV-2026-00009 | Foshan Capacitor Works | 2025-04-02 | 280 | 0 |
| ACC-PINV-2026-00010 | Suzhou Lamination Industries | 2025-04-14 | 15,000 | 0 |
| ACC-PINV-2026-00011 | Hangzhou Precision Bearings | 2025-04-28 | 360 | 0 |
| ACC-PINV-2026-00012 | Tongling Magnet Wire Co. | 2025-05-06 | 9,540 | 9,540 |
| ACC-PINV-2026-00013 | Ningbo Copper Tube Co. | 2025-05-19 | 535 | 0 |
| ACC-PINV-2026-00014 | Hangzhou Precision Bearings | 2025-06-03 | 1,253 | 0 |
| ACC-PINV-2026-00015 | Yantai Refrigerant Solutions | 2025-06-17 | 137 | 0 |
| ACC-PINV-2026-00016 | Foshan Capacitor Works | 2025-06-24 | 43 | 0 |
| ACC-PINV-2026-00017 | Suzhou Lamination Industries | 2025-07-01 | 11,400 | 11,400 |
| ACC-PINV-2026-00018 | Foshan Capacitor Works | 2025-07-22 | 264 | 0 |
| ACC-PINV-2026-00019 | Hangzhou Precision Bearings | 2025-08-05 | 1,392 | 0 |
| ACC-PINV-2026-00020 | Ningbo Copper Tube Co. | 2025-08-19 | 324 | 324 |
| ACC-PINV-2026-00021 | Tongling Magnet Wire Co. | 2025-09-02 | 2,925 | 0 |

**Total AP:** $22,784. **AP by supplier:** Suzhou Lamination Industries $11,400, Tongling Magnet Wire Co. $9,540, Hangzhou Precision Bearings $1,520, Ningbo Copper Tube Co. $324.

> Purchase Invoice `due_date` defaults to the posting date (an ERPNext default we did
> not override), so avoid questions that depend on purchase-invoice overdue status.

## Work Orders

| # | Date | Item | Qty | Status |
|---|---|---|---:|---|
| MFG-WO-2026-00001 | 2025-02-10 | SA-MOTOR-1HP | 40 | Completed |
| MFG-WO-2026-00002 | 2025-02-17 | SA-PUMP-R32 | 40 | Completed |
| MFG-WO-2026-00003 | 2025-03-03 | FG-COMP-1HP-R32 | 20 | Completed |
| MFG-WO-2026-00004 | 2025-03-24 | SA-PUMP-R12 | 20 | Completed |
| MFG-WO-2026-00005 | 2025-04-07 | FG-COMP-2HP-R12 | 10 | Completed |
| MFG-WO-2026-00006 | 2025-04-21 | SA-MOTOR-1HP | 40 | Completed |
| MFG-WO-2026-00007 | 2025-05-05 | SA-PUMP-R32 | 40 | Completed |
| MFG-WO-2026-00008 | 2025-05-12 | FG-COMP-1HP-R32 | 25 | Completed |
| MFG-WO-2026-00009 | 2025-06-09 | FG-COMP-1.5HP-R32 | 15 | Completed |
| MFG-WO-2026-00010 | 2025-06-23 | SA-MOTOR-1HP | 40 | Completed |
| MFG-WO-2026-00011 | 2025-07-07 | SA-PUMP-R32 | 40 | Completed |
| MFG-WO-2026-00012 | 2025-07-14 | FG-COMP-1HP-R32 | 30 | Completed |
| MFG-WO-2026-00013 | 2025-07-21 | FG-COMP-2HP-R12 | 10 | Completed |
| MFG-WO-2026-00014 | 2025-08-04 | SA-MOTOR-1HP | 40 | Completed |
| MFG-WO-2026-00015 | 2025-08-11 | SA-PUMP-R32 | 35 | Completed |
| MFG-WO-2026-00016 | 2025-08-25 | FG-COMP-1.5HP-R32 | 20 | Completed |
| MFG-WO-2026-00017 | 2025-09-08 | SA-MOTOR-1HP | 15 | Completed |
| MFG-WO-2026-00018 | 2025-09-15 | FG-COMP-1HP-R32 | 25 | Completed |
| MFG-WO-2026-00019 | 2025-10-06 | SA-PUMP-R12 | 10 | In Process |
| MFG-WO-2026-00020 | 2025-10-10 | FG-COMP-1.5HP-R32 | 30 | Not Started |

`MFG-WO-2026-00019` has its materials transferred to Work In Progress and is not yet
manufactured. `MFG-WO-2026-00020` cannot start: three required lines are short.

### MFG-WO-2026-00020 shortage detail

| Required Item | Required | In Stores | Short by |
|---|---:|---:|---:|
| SA-MOTOR-1HP | 30 | 20 | **10** |
| SA-PUMP-R32 | 30 | 20 | **10** |
| RM-CAP-RUN-25 | 30 | 205 | ok |
| RM-DISCH-PIPE-CU | 30 | 185 | ok |
| RM-COIL-CU-2.0 | 60 | 50 | **10** |

## Payments

| # | Date | Type | Party | Amount |
|---|---|---|---|---:|
| ACC-PAY-2026-00001 | 2025-01-13 | Pay | Tongling Magnet Wire Co. | 12,200 |
| ACC-PAY-2026-00002 | 2025-01-20 | Pay | Foshan Capacitor Works | 320 |
| ACC-PAY-2026-00003 | 2025-01-27 | Pay | Suzhou Lamination Industries | 14,800 |
| ACC-PAY-2026-00004 | 2025-02-17 | Pay | Ningbo Copper Tube Co. | 530 |
| ACC-PAY-2026-00005 | 2025-02-25 | Pay | Yantai Refrigerant Solutions | 272 |
| ACC-PAY-2026-00006 | 2025-03-10 | Pay | Tongling Magnet Wire Co. | 5,640 |
| ACC-PAY-2026-00007 | 2025-03-17 | Receive | GreenAir HVAC Solutions | 6,000 |
| ACC-PAY-2026-00008 | 2025-03-23 | Pay | Hangzhou Precision Bearings | 1,610 |
| ACC-PAY-2026-00009 | 2025-03-27 | Receive | BlueRidge Cooling Systems | 3,540 |
| ACC-PAY-2026-00010 | 2025-04-07 | Pay | Foshan Capacitor Works | 280 |
| ACC-PAY-2026-00011 | 2025-04-19 | Pay | Suzhou Lamination Industries | 15,000 |
| ACC-PAY-2026-00012 | 2025-04-21 | Receive | Summit Climate OEM | 4,250 |
| ACC-PAY-2026-00013 | 2025-04-29 | Receive | Polaris Climate Tech | 2,320 |
| ACC-PAY-2026-00014 | 2025-05-03 | Pay | Hangzhou Precision Bearings | 360 |
| ACC-PAY-2026-00015 | 2025-05-22 | Receive | GreenAir HVAC Solutions | 7,200 |
| ACC-PAY-2026-00016 | 2025-05-24 | Pay | Ningbo Copper Tube Co. | 535 |
| ACC-PAY-2026-00017 | 2025-05-27 | Receive | Summit Climate OEM | 1,200 |
| ACC-PAY-2026-00018 | 2025-06-04 | Receive | Cascade Thermal Systems | 2,580 |
| ACC-PAY-2026-00019 | 2025-06-09 | Receive | Helio Comfort Appliances | 3,630 |
| ACC-PAY-2026-00020 | 2025-06-08 | Pay | Hangzhou Precision Bearings | 1,253 |
| ACC-PAY-2026-00021 | 2025-06-23 | Receive | Nordic Air Industries | 7,200 |
| ACC-PAY-2026-00022 | 2025-06-22 | Pay | Yantai Refrigerant Solutions | 137 |
| ACC-PAY-2026-00023 | 2025-06-29 | Pay | Foshan Capacitor Works | 43 |
| ACC-PAY-2026-00024 | 2025-07-07 | Receive | Meridian HVAC Group | 6,600 |
| ACC-PAY-2026-00025 | 2025-07-27 | Pay | Foshan Capacitor Works | 264 |
| ACC-PAY-2026-00026 | 2025-08-01 | Receive | Summit Climate OEM | 5,100 |
| ACC-PAY-2026-00027 | 2025-08-10 | Pay | Hangzhou Precision Bearings | 1,392 |
| ACC-PAY-2026-00028 | 2025-08-19 | Receive | BlueRidge Cooling Systems | 2,360 |
| ACC-PAY-2026-00029 | 2025-09-07 | Pay | Tongling Magnet Wire Co. | 2,925 |
| ACC-PAY-2026-00030 | 2025-09-10 | Receive | Cascade Thermal Systems | 3,440 |
| ACC-PAY-2026-00031 | 2025-10-01 | Receive | Meridian HVAC Group | 3,570 |

**Cash:** received $58,990, paid $57,561, net $1,429.

---

## Sample queries

Each query below has a **deterministic answer** the data is designed to produce. Use
them as a self-test harness while building your agent. We grade with a held-out set of
queries of the same shapes.

### Read (single DocType)

1. **"What's the current stock of copper coil?"**
   → 50 m of `RM-COIL-CU-2.0` in `Stores - CCM` (200 m more on order, 60 m reserved for a work order).
2. **"List all open purchase orders."**
   → 6 POs with status `To Receive and Bill`, total $15,065.50.
3. **"Which customer placed the most sales orders?"**
   → GreenAir HVAC Solutions, 5 orders (Summit Climate OEM is next with 4).

### Cross-DocType

4. **"Which components are blocking Work Order MFG-WO-2026-00020?"**
   → `SA-MOTOR-1HP` (need 30, have 20), `SA-PUMP-R32` (need 30, have 20),
     `RM-COIL-CU-2.0` (need 60, have 50). Three shortages of 10 each.
5. **"What's the gross margin on the 1HP/R32 compressor?"**
   → No single number: the answer must state its basis. Cost is BOM / item
     valuation $575.20 (stock-ledger actual $566.81 also acceptable). Price is
     list $600 or realized sales-order rates $580–$610. Margin must be
     consistent with the chosen bases: $24.80 (4.1%) at list on BOM cost,
     $4.80–$34.80 over realized orders.
6. **"Show me overdue sales invoices."**
   → Four, total $25,380: `ACC-SINV-2026-00011` GreenAir $6,000 (due 2025-08-17),
     `-00013` Polaris $4,640 (2025-08-31), `-00015` Helio $8,640 (2025-09-28),
     `-00017` GreenAir $6,100 (2025-10-10). Not `-00018`, `-00020`, `-00021`:
     unpaid but not yet due, whatever their `status` field says.
