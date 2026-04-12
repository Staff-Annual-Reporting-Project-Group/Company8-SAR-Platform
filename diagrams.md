# SAR Platform — ERD & Class Diagrams

## Entity Relationship Diagram

```mermaid
erDiagram
    USER {
        int id PK
        string username
        string first_name
        string last_name
        string email
        string password
        bool is_active
        bool is_staff
        bool is_superuser
    }

    USERPROFILEPIC {
        int id PK
        int user_id FK
        string profilePic
        string phone
        string gender
    }

    REPORT {
        int id PK
        int user_id FK
        int category_id FK
        string title
        text description
        string feature_image
        date date_of_report
        datetime created
        datetime updated
        bool isActive
    }

    CATEGORY {
        int id PK
        string name
        text regex
    }

    COMMITTEE {
        int id PK
        string name
    }

    PARTICIPANT {
        int id PK
        int user_id FK
        string name
    }

    REPORT_COMMITTEES {
        int report_id FK
        int committee_id FK
    }

    REPORT_PARTICIPANTS {
        int report_id FK
        int participant_id FK
    }

    USER ||--o| USERPROFILEPIC : "has profile pic"
    USER ||--o{ REPORT : "authors"
    USER ||--o{ PARTICIPANT : "linked to"
    REPORT }o--|| CATEGORY : "belongs to"
    REPORT ||--o{ REPORT_COMMITTEES : "in"
    COMMITTEE ||--o{ REPORT_COMMITTEES : "has"
    REPORT ||--o{ REPORT_PARTICIPANTS : "involves"
    PARTICIPANT ||--o{ REPORT_PARTICIPANTS : "participates in"
```

---

## Class Diagram

### Models

```mermaid
classDiagram
    class User {
        +int id
        +string username
        +string first_name
        +string last_name
        +string email
        +string password
        +bool is_active
        +bool is_staff
        +bool is_superuser
    }

    class UserProfilePic {
        +int id
        +User user
        +ImageField profilePic
        +string phone
        +string gender
        +__str__() string
    }

    class Report {
        +int id
        +User user
        +Category category
        +string title
        +TextField description
        +ImageField feature_image
        +date date_of_report
        +datetime created
        +datetime updated
        +bool isActive
        +ManyToMany participants
        +ManyToMany committees
        +__str__() string
    }

    class ReportQuerySet {
        +active() QuerySet
        +user_reports(user) QuerySet
        +search(keyword) QuerySet
        +filterReports(period, report_type, committee, participant) QuerySet
    }

    class Category {
        +int id
        +string name
        +TextField regex
        +__str__() string
    }

    class Committee {
        +int id
        +string name
        +__str__() string
    }

    class Participant {
        +int id
        +User user
        +string name
        +__str__() string
    }

    User "1" --> "0..1" UserProfilePic : profile_pic
    User "1" --> "0..*" Report : reports
    User "1" --> "0..*" Participant : linked to
    Report "0..*" --> "1" Category : category
    Report "0..*" --> "0..*" Committee : committees
    Report "0..*" --> "0..*" Participant : participants
    Report ..> ReportQuerySet : uses
```

### Views

```mermaid
classDiagram
    class ReportsViews {
        <<module: reports/views.py>>
        +index(request) HttpResponse
        +reportView(request, pk) HttpResponse
        +selectedUserReportsView(request, pk) HttpResponse
        +deleteReport(request, pk) HttpResponse
        +annual_report(request) HttpResponse
        +annual_report_pdf(request) FileResponse
        +my_reports_pdf(request) FileResponse
    }

    class UsersViews {
        <<module: users/views.py>>
        +loginPage(request) HttpResponse
        +logout_view(request) HttpResponse
        +profile_view(request) HttpResponse
        +create_report_view(request) HttpResponse
        +edit_report_view(request, pk) HttpResponse
        +delete_report(request, pk) HttpResponse
        +account_view(request) HttpResponse
        +registerView(request) HttpResponse
    }

    class AdministrationViews {
        <<module: administration/views.py>>
        +adminAccountView(request) HttpResponse
        +adminReportView(request) HttpResponse
    }

    class ReportsViews_Models {
        <<uses>>
    }

    ReportsViews ..> Report : queries
    ReportsViews ..> Category : queries
    ReportsViews ..> Committee : queries
    ReportsViews ..> Participant : queries

    UsersViews ..> Report : creates/edits/deletes
    UsersViews ..> Category : queries
    UsersViews ..> Committee : queries
    UsersViews ..> Participant : creates
    UsersViews ..> User : auth/register
    UsersViews ..> UserProfilePic : updates

    AdministrationViews ..> User : activate/deactivate
    AdministrationViews ..> UserProfilePic : queries
    AdministrationViews ..> Report : soft-deletes
    AdministrationViews ..> Category : queries
    AdministrationViews ..> Committee : queries
```

---

## URL → View Mapping

| URL | View | App |
|-----|------|-----|
| `/reports/` | `index` | reports |
| `/reports/report/<pk>` | `reportView` | reports |
| `/reports/report/delete/<pk>` | `deleteReport` | reports |
| `/reports/annual-report/` | `annual_report` | reports |
| `/reports/annual/pdf/` | `annual_report_pdf` | reports |
| `/reports/my-reports/pdf/` | `my_reports_pdf` | reports |
| `/reports/reports/user/<pk>/` | `selectedUserReportsView` | reports |
| `/users/login/` | `loginPage` | users |
| `/users/logout/` | `logout_view` | users |
| `/users/profile/` | `profile_view` | users |
| `/users/profile/create-report` | `create_report_view` | users |
| `/users/profile/edit-report/<pk>` | `edit_report_view` | users |
| `/users/delete-report/<pk>` | `delete_report` | users |
| `/users/account/` | `account_view` | users |
| `/users/register/` | `registerView` | users |
| `/administration/admin-accounts/` | `adminAccountView` | administration |
| `/administration/admin-reports/` | `adminReportView` | administration |
