"""
modules/employees.py - Staff & Employee Management
Allows Admin to onboard new staff, assign roles/departments, manage salaries, and track duties.
"""

from database import execute_query, fetch_all, fetch_one
from modules.auth import register_user

DEPARTMENTS = ('Operations', 'Ticketing', 'Catering', 'Maintenance', 'Management')
SHIFTS = (
    'Morning (06:00 - 14:00)',
    'Evening (14:00 - 22:00)',
    'Night (22:00 - 06:00)',
    'General / Flexible'
)


def generate_employee_code() -> str:
    """Generate next sequential employee code e.g. EMP-1001."""
    last_emp = fetch_one("SELECT id FROM employees ORDER BY id DESC LIMIT 1")
    next_num = 1001 if not last_emp else 1001 + last_emp['id']
    return f"EMP-{next_num}"


def add_employee(full_name: str, role_title: str, department: str,
                 contact: str, salary: float, shift: str = None,
                 assigned_to: str = 'HQ / General',
                 create_login: bool = False, username: str = None,
                 password: str = None, email: str = None) -> tuple:
    """
    Onboard a new employee. Optionally create login credentials with 'staff' role.
    Returns (success: bool, message: str, employee_id: int or None).
    """
    name = full_name.strip()
    title = role_title.strip()
    dept = department.strip()
    phone = contact.strip()

    if not name or not title:
        return False, "Full name and role title are required.", None

    if dept not in DEPARTMENTS:
        return False, f"Invalid department. Must be one of: {', '.join(DEPARTMENTS)}", None

    emp_shift = shift if shift in SHIFTS else SHIFTS[0]
    emp_code = generate_employee_code()
    linked_user_id = None

    # Optionally create a linked user account for system access
    if create_login:
        if not username or not password:
            return False, "Username and password required to create login account.", None

        staff_email = email.strip() if email else f"{username.lower()}@trainsystem.org"
        reg_ok, reg_msg, new_uid = register_user(
            username=username,
            password=password,
            full_name=name,
            email=staff_email,
            phone=phone if len(phone) == 10 else "9876543210",
            role='staff'
        )
        if not reg_ok:
            return False, f"Failed to create staff login account: {reg_msg}", None
        linked_user_id = new_uid

    try:
        emp_id = execute_query(
            """
            INSERT INTO employees (user_id, employee_code, full_name, role_title, department,
                                   contact, salary, shift, status, assigned_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
            """,
            (linked_user_id, emp_code, name, title, dept, phone, max(0.0, float(salary)), emp_shift, assigned_to)
        )
        login_note = f" (Login created: {username})" if create_login else ""
        return True, f"Employee {name} onboarded successfully with ID {emp_code}{login_note}.", emp_id
    except Exception as e:
        return False, f"Failed to add employee: {str(e)}", None


def get_all_employees(department: str = None, status: str = None) -> list:
    """Retrieve list of employees with optional filters."""
    query = """
    SELECT e.*, u.username, u.email
    FROM employees e
    LEFT JOIN users u ON e.user_id = u.id
    WHERE 1=1
    """
    params = []
    if department:
        query += " AND e.department = ?"
        params.append(department)
    if status:
        query += " AND e.status = ?"
        params.append(status)

    query += " ORDER BY e.id ASC"
    return fetch_all(query, tuple(params))


def get_employee_by_id(emp_id: int) -> dict:
    """Get employee details by primary ID."""
    return fetch_one(
        """
        SELECT e.*, u.username, u.email
        FROM employees e
        LEFT JOIN users u ON e.user_id = u.id
        WHERE e.id = ?
        """,
        (emp_id,)
    )


def get_employee_by_code(emp_code: str) -> dict:
    """Get employee details by employee code (e.g. EMP-1001)."""
    return fetch_one(
        """
        SELECT e.*, u.username, u.email
        FROM employees e
        LEFT JOIN users u ON e.user_id = u.id
        WHERE e.employee_code = ?
        """,
        (emp_code.strip().upper(),)
    )


def get_employee_by_user_id(user_id: int) -> dict:
    """Fetch staff profile linked to logged-in user account."""
    return fetch_one("SELECT * FROM employees WHERE user_id = ?", (user_id,))


def update_employee(emp_id: int, full_name: str, role_title: str,
                    department: str, contact: str, salary: float,
                    shift: str, status: str, assigned_to: str) -> tuple:
    """Update employee demographic and employment records."""
    if department not in DEPARTMENTS:
        return False, f"Invalid department. Must be one of: {', '.join(DEPARTMENTS)}"

    if status not in ('ACTIVE', 'ON_LEAVE', 'INACTIVE'):
        return False, "Invalid status. Must be ACTIVE, ON_LEAVE, or INACTIVE."

    try:
        execute_query(
            """
            UPDATE employees
            SET full_name = ?, role_title = ?, department = ?, contact = ?,
                salary = ?, shift = ?, status = ?, assigned_to = ?
            WHERE id = ?
            """,
            (full_name.strip(), role_title.strip(), department.strip(),
             contact.strip(), float(salary), shift.strip(), status.strip(),
             assigned_to.strip(), emp_id)
        )
        return True, f"Employee ID {emp_id} updated successfully."
    except Exception as e:
        return False, f"Failed to update employee: {str(e)}"


def delete_employee(emp_id: int) -> tuple:
    """Remove employee record."""
    try:
        execute_query("DELETE FROM employees WHERE id = ?", (emp_id,))
        return True, f"Employee ID {emp_id} removed from system."
    except Exception as e:
        return False, f"Failed to delete employee: {str(e)}"
