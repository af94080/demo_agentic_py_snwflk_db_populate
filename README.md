## **This agentic program takes a plain-English request, uses ChatGPT to decide the steps, and builds demo databases in Snowflake with related tables and sample data, such as these:**

- DEMO_OCT_31_CELL_PHONE_USAGE: COUNTRIES, PLANS and USAGE tables, linked by COUNTRY_ID.
- DEMO_OCT_31_HOSPITAL_SCHEDULING: PATIENTS, DOCTORS and APPOINTMENTS tables, linked by PATIENT_ID and DOCTOR_ID.
- DEMO_OCT_31_RETAIL_SALES: CUSTOMERS, ORDERS and PRODUCTS tables, with ORDERS linked to CUSTOMERS by CUSTOMER_ID.

```mermaid
erDiagram
    COUNTRIES ||--o{ PLANS : "COUNTRY_ID"
    COUNTRIES ||--o{ USAGE : "COUNTRY_ID"
    COUNTRIES {
        int COUNTRY_ID PK
        string NAME
        int POPULATION
    }
    PLANS {
        int PLAN_ID PK
        int COUNTRY_ID FK
    }
    USAGE {
        int USAGE_ID PK
        int COUNTRY_ID FK
    }
```

```mermaid
erDiagram
    PATIENTS ||--o{ APPOINTMENTS : "PATIENT_ID"
    DOCTORS ||--o{ APPOINTMENTS : "DOCTOR_ID"
    PATIENTS {
        int PATIENT_ID PK
    }
    DOCTORS {
        int DOCTOR_ID PK
        string FIRST_NAME
        string LAST_NAME
        string SPECIALTY
    }
    APPOINTMENTS {
        int APPOINTMENT_ID PK
        int PATIENT_ID FK
        int DOCTOR_ID FK
    }
```

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : "CUSTOMER_ID"
    CUSTOMERS {
        int CUSTOMER_ID PK
    }
    ORDERS {
        int ORDER_ID PK
        int CUSTOMER_ID FK
    }
    PRODUCTS {
        int PRODUCT_ID PK
        string NAME
        string CATEGORY
        decimal PRICE
    }
```
