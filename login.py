import streamlit as st
import mysql.connector
import datetime
import pandas as pd


# DB Connection
# ─────────────────────────────────────────
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Rv171020",
    database="sales_management_system"
)
mycursor = mydb.cursor()


for key, default in [
    ("logged_in", False),
    ("user", None),
    ("branch_id", None),
    ("is_superadmin", False),
    ("action", None),
    ("prev_section", None),
    ("selected_summary_branch", None),   
    ("selected_summary_product", None),  
]:
    if key not in st.session_state:
        st.session_state[key] = default



def fetch_all(query, params=()):
    mycursor.execute(query, params)
    return mycursor.fetchall()


def get_distinct(column, table, branch_id=None, is_superadmin=True):
    """Return sorted distinct non-null values from a column, optionally filtered by branch."""
    if is_superadmin or branch_id is None:
        rows = fetch_all(
            f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY {column}"
        )
    else:
        rows = fetch_all(
            f"SELECT DISTINCT {column} FROM {table} WHERE branch_id=%s AND {column} IS NOT NULL ORDER BY {column}",
            (branch_id,)
        )
    return [r[0] for r in rows]



# LOGIN PAGE
# ─────────────────────────────────────────
def login_page():

    st.set_page_config(page_title="VR-SHOPPING", page_icon="🛒", layout="centered")

    st.markdown("""
        <style>
        .login-title { font-size: 2.5rem; font-weight: 800; color: #1a1a2e; }
        .login-sub   { color: #555; margin-bottom: 1.5rem; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-title">🛒 VR-SHOPPING</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Sales Management System — Please log in</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    username  = st.text_input("Username", placeholder="Enter your username")
    password  = st.text_input("Password", type="password", placeholder="Enter your password")
    branch_id = st.text_input("Branch ID", placeholder="Leave empty for Super Admin")

    if st.button("Login"):
        if username == "superadmin" and password == "admin@123":
            st.session_state.update(logged_in=True, is_superadmin=True, user=(None, "Super Admin"), branch_id=None)
            st.rerun()
        elif username and password and branch_id:
            mycursor.execute(
                "SELECT * FROM users WHERE username=%s AND password=%s AND branch_id=%s",
                (username, password, branch_id)
            )
            user = mycursor.fetchone()
            if user:
                st.session_state.update(logged_in=True, is_superadmin=False, user=user, branch_id=branch_id)
                st.rerun()
            else:
                st.error("Invalid credentials or Branch ID.")
        else:
            st.warning("Please fill all fields, or use Super Admin credentials.")
    st.markdown('</div>', unsafe_allow_html=True)



# DYNAMIC SUMMARY  (with clickable branch cards)
# ─────────────────────────────────────────
def show_summary(branch_id=None, is_superadmin=True,
                 start_date=None, end_date=None,
                 filter_product=None, filter_branch=None):
    """
    Show filtered gross / received / pending summary as metric cards.
    Each branch card is clickable — clicking it sets session_state.selected_summary_branch
    so the records table below can drill into that branch.
    """

    conditions, params = [], []

    if not is_superadmin and branch_id:
        conditions.append("cs.branch_id = %s")
        params.append(branch_id)
    elif is_superadmin and filter_branch and filter_branch != "All Branches":
        conditions.append("cs.branch_id = %s")
        params.append(filter_branch)

    if start_date:
        conditions.append("cs.date >= %s")
        params.append(start_date)

    if end_date:
        conditions.append("cs.date <= %s")
        params.append(end_date)

    if filter_product and filter_product != "All Products":
        conditions.append("cs.product_name = %s")
        params.append(filter_product)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    rows = fetch_all(f"""
        SELECT cs.branch_id,
               b.branch_name,
               SUM(cs.gross_sales)     AS total_gross,
               SUM(cs.received_amount) AS total_received,
               SUM(cs.pending_amount)  AS total_pending
        FROM customer_sales cs
        LEFT JOIN branches b ON cs.branch_id = b.branch_id
        {where}
        GROUP BY cs.branch_id, b.branch_name
        ORDER BY cs.branch_id
    """, tuple(params))

    st.markdown("Sales Summary")
    st.caption("Click a branch button below to view its detailed records.")

    if not rows:
        st.info("No sales data matches the selected filters.")
        return

    
    if st.session_state.selected_summary_branch is not None:
        if st.button("Show All Branches", key="reset_branch_btn"):
            st.session_state.selected_summary_branch = None
            st.session_state.selected_summary_product = None
            st.rerun()

    for row in rows:
        bid, bname, gross, received, pending = row
        gross    = float(gross    or 0)
        received = float(received or 0)
        pending  = float(pending  or 0)
        display_name = bname if bname else str(bid)

        
        tag_col, _ = st.columns([3, 1])
        with tag_col:
            tag_parts = []
            if filter_product and filter_product != "All Products":
                tag_parts.append(f"{filter_product}")
            if start_date and end_date:
                tag_parts.append(f"{start_date} → {end_date}")
            elif start_date:
                tag_parts.append(f"From {start_date}")
            elif end_date:
                tag_parts.append(f"Up to {end_date}")

            extra = ("  |  " + "  |  ".join(tag_parts)) if tag_parts else ""

            
            is_selected = (st.session_state.selected_summary_branch == bid)
            btn_label   = f"{ ''if is_selected else ''}{display_name}{extra}"

            if st.button(btn_label, key=f"branch_btn_{bid}"):
                if st.session_state.selected_summary_branch == bid:
                    
                    st.session_state.selected_summary_branch = None
                    st.session_state.selected_summary_product = None
                else:
                    st.session_state.selected_summary_branch = bid
                    st.session_state.selected_summary_product = None
                st.rerun()

        c1, c2, c3 = st.columns(3)
        c1.metric(" Gross Sales",     f"₹{gross:,.2f}")
        c2.metric(" Received Amount", f"₹{received:,.2f}")
        c3.metric(" Pending Amount",  f"₹{pending:,.2f}")
        st.markdown("---")


# CUSTOMER SALES SECTION
# ─────────────────────────────────────────
def section_customer_sales(branch_id, is_superadmin):
    st.subheader("Customer Sales")

    #  Filter row 
    st.markdown("Filters")
    num_cols    = 4 if is_superadmin else 3
    filter_cols = st.columns(num_cols)

    filter_branch = None
    if is_superadmin:
        branch_rows        = fetch_all("SELECT branch_id, branch_name FROM branches ORDER BY branch_name")
        branch_name_to_id  = {row[1]: row[0] for row in branch_rows}
        branch_names       = [row[1] for row in branch_rows]

        selected_branch_name = filter_cols[0].selectbox(
            "Branch", ["All Branches"] + branch_names, key="sf_branch"
        )
        filter_branch = branch_name_to_id.get(selected_branch_name) if selected_branch_name != "All Branches" else None

    date_start_idx = 1 if is_superadmin else 0
    date_end_idx   = 2 if is_superadmin else 1
    prod_idx       = 3 if is_superadmin else 2

    filter_start_date = filter_cols[date_start_idx].date_input(
        "Start Date", value=None, key="sf_start_date"
    )
    filter_end_date = filter_cols[date_end_idx].date_input(
        "End Date", value=None, key="sf_end_date"
    )

    products       = get_distinct("product_name", "customer_sales", branch_id=branch_id, is_superadmin=is_superadmin)
    filter_product = filter_cols[prod_idx].selectbox(
        "Product", ["All Products"] + products, key="sf_product"
    )

    st.divider()

   
    show_summary(
        branch_id=branch_id,
        is_superadmin=is_superadmin,
        start_date=filter_start_date,
        end_date=filter_end_date,
        filter_product=filter_product,
        filter_branch=filter_branch,
    )

    st.divider()

    
    # DRILL-DOWN: records for clicked branch
    # ─────────────────────────────────────────
    clicked_branch = st.session_state.selected_summary_branch

    if clicked_branch is not None:
        # Resolve branch name for display
        name_row = fetch_all(
            "SELECT branch_name FROM branches WHERE branch_id = %s", (clicked_branch,)
        )
        clicked_branch_name = name_row[0][0] if name_row else str(clicked_branch)

        st.markdown(f"### Records for Branch: **{clicked_branch_name}**")

        branch_products = fetch_all(
            "SELECT DISTINCT product_name FROM customer_sales "
            "WHERE branch_id = %s AND product_name IS NOT NULL ORDER BY product_name",
            (clicked_branch,)
        )
        branch_product_list = [r[0] for r in branch_products]

        selected_drill_product = st.selectbox(
            "Filter by Product",
            ["All Products"] + branch_product_list,
            key="drill_product_select"
        )

        drill_conditions = ["cs.branch_id = %s"]
        drill_params     = [clicked_branch]

        if selected_drill_product and selected_drill_product != "All Products":
            drill_conditions.append("cs.product_name = %s")
            drill_params.append(selected_drill_product)

        if filter_start_date:
            drill_conditions.append("cs.date >= %s")
            drill_params.append(filter_start_date)

        if filter_end_date:
            drill_conditions.append("cs.date <= %s")
            drill_params.append(filter_end_date)

        drill_where = "WHERE " + " AND ".join(drill_conditions)

        drill_data = fetch_all(f"""
            SELECT cs.sale_id, cs.branch_id, cs.date, cs.name,
                   cs.mobile_number, cs.product_name,
                   cs.gross_sales, cs.received_amount, cs.pending_amount, cs.status
            FROM customer_sales cs
            {drill_where}
            ORDER BY cs.date DESC
        """, tuple(drill_params))

        if drill_data:
            df_drill = pd.DataFrame(drill_data, columns=[
                "Sale ID", "Branch ID", "Date", "Customer Name",
                "Mobile Number", "Product Name", "Gross Sales",
                "Received Amount", "Pending Amount", "Status"
            ])
            st.dataframe(df_drill, use_container_width=True)

            total_gross    = df_drill["Gross Sales"].astype(float).sum()
            total_received = df_drill["Received Amount"].astype(float).sum()
            total_pending  = df_drill["Pending Amount"].astype(float).sum()
            s1, s2, s3 = st.columns(3)
            s1.metric("Total Gross",    f"₹{total_gross:,.2f}")
            s2.metric("Total Received", f"₹{total_received:,.2f}")
            s3.metric("Total Pending",  f"₹{total_pending:,.2f}")
        else:
            st.info("No records found for this branch / filters.")

        st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("View All Sales Records"):
            st.session_state.action = "view_sales"
    with col2:
        if st.button("New Sales Entry"):
            st.session_state.action = "insert_sales"

    if st.session_state.action == "view_sales":
        st.markdown("### Sales Records")

        conditions, params = [], []

        if not is_superadmin:
            conditions.append("branch_id = %s"); params.append(branch_id)
        elif filter_branch and filter_branch != "All Branches":
            conditions.append("branch_id = %s"); params.append(filter_branch)

        if filter_start_date:
            conditions.append("date >= %s"); params.append(filter_start_date)

        if filter_end_date:
            conditions.append("date <= %s"); params.append(filter_end_date)

        if filter_product and filter_product != "All Products":
            conditions.append("product_name = %s"); params.append(filter_product)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        data  = fetch_all(f"SELECT * FROM customer_sales {where} ORDER BY date DESC", tuple(params))

        if data:
            df = pd.DataFrame(data, columns=[
                "Sale ID", "Branch ID", "Date", "Customer Name",
                "Mobile Number", "Product Name", "Gross Sales",
                "Received Amount", "Pending Amount", "Status"
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No records match the selected filters.")

    elif st.session_state.action == "insert_sales":
        st.markdown("### Add New Customer Sale")

        result  = fetch_all("SELECT MAX(sale_id) FROM customer_sales")
        max_sid = result[0][0] if result and result[0][0] is not None else 0
        next_sale_id = int(max_sid) + 1
        st.info(f"Sale ID (Auto): **{next_sale_id}**")

        entry_branch_id = st.text_input("Branch ID", value=branch_id if not is_superadmin else "")
        date            = st.date_input("Date", value=datetime.date.today(), key="cs_date")
        name            = st.text_input("Customer Name")
        mobile_number   = st.text_input("Mobile Number")
        product_name    = st.text_input("Product Name")
        gross_sales     = st.text_input("Gross Sales Amount")

        if st.button("Submit Sale"):
            if not all([entry_branch_id, name, mobile_number, product_name, gross_sales]):
                st.warning("Please fill all required fields.")
            else:
                mycursor.execute("""
                    INSERT INTO customer_sales
                    (sale_id, branch_id, date, name, mobile_number, product_name, gross_sales)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (next_sale_id, entry_branch_id, date, name, mobile_number,
                      product_name, gross_sales))
                mydb.commit()
                st.success("Sale submitted successfully!")
                st.session_state.action = None


# PAYMENT SPLITS SECTION
# ─────────────────────────────────────────
def section_payment_splits(branch_id, is_superadmin):
    st.subheader("Payment Splits")

    st.markdown("##### Filters")
    num_cols    = 3 if is_superadmin else 2
    filter_cols = st.columns(num_cols)

    filter_branch = None
    if is_superadmin:

        branch_rows       = fetch_all("SELECT branch_id, branch_name FROM branches ORDER BY branch_name")
        branch_name_to_id = {row[1]: row[0] for row in branch_rows}
        branch_names      = [row[1] for row in branch_rows]

        selected_branch_name = filter_cols[0].selectbox(
            "Branch", ["All Branches"] + branch_names, key="pf_branch"
        )
        filter_branch = branch_name_to_id.get(selected_branch_name) if selected_branch_name != "All Branches" else None

    method_idx  = 1 if is_superadmin else 0
    methods     = fetch_all(
        "SELECT DISTINCT payment_method FROM payment_splits WHERE payment_method IS NOT NULL ORDER BY payment_method"
    )
    method_list   = [r[0] for r in methods]
    filter_method = filter_cols[method_idx].selectbox(
        "Payment Method", ["All Methods"] + method_list, key="pf_method"
    )

    sid_idx = 2 if is_superadmin else 1
    if is_superadmin:
        if filter_branch:


            sale_ids = fetch_all(
                "SELECT DISTINCT ps.sale_id FROM payment_splits ps "
                "JOIN customer_sales cs ON ps.sale_id = cs.sale_id "
                "WHERE cs.branch_id = %s ORDER BY ps.sale_id",
                (filter_branch,)
            )
        else:
            sale_ids = fetch_all("SELECT DISTINCT sale_id FROM payment_splits ORDER BY sale_id")
    else:
        sale_ids = fetch_all(
            "SELECT DISTINCT ps.sale_id FROM payment_splits ps "
            "JOIN customer_sales cs ON ps.sale_id = cs.sale_id "
            "WHERE cs.branch_id = %s ORDER BY ps.sale_id",
            (branch_id,)
        )
    sid_list    = [str(r[0]) for r in sale_ids]
    filter_sale = filter_cols[sid_idx].selectbox(
        "Sale ID", ["All Sales"] + sid_list, key="pf_sale"
    )

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("View Payment Splits"):
            st.session_state.action = "view_payment"
    with col2:
        if st.button("New Payment Entry"):
            st.session_state.action = "insert_payment"

    if st.session_state.action == "view_payment":
        st.markdown("### Payment Records")

        conditions, params = [], []

        if not is_superadmin:
            conditions.append("sale_id IN (SELECT sale_id FROM customer_sales WHERE branch_id = %s)")
            params.append(branch_id)
        elif filter_branch:
            conditions.append("sale_id IN (SELECT sale_id FROM customer_sales WHERE branch_id = %s)")
            params.append(filter_branch)

        if filter_method and filter_method != "All Methods":
            conditions.append("payment_method = %s"); params.append(filter_method)

        if filter_sale and filter_sale != "All Sales":
            conditions.append("sale_id = %s"); params.append(filter_sale)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        data  = fetch_all(f"SELECT * FROM payment_splits {where}", tuple(params))

        if data:
            df = pd.DataFrame(data, columns=[
                "Payment ID", "Sale ID", "Payment Date", "Amount Paid", "Payment Method"
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No payment records match the selected filters.")

    elif st.session_state.action == "insert_payment":
        st.markdown("### Add New Payment Split")

        result = fetch_all("SELECT MAX(payment_id) FROM payment_splits")
        max_pid = result[0][0] if result and result[0][0] is not None else 0
        next_payment_id = int(max_pid) + 1
        st.info(f"Payment ID (Auto): **{next_payment_id}**")

        result2 = fetch_all("SELECT MAX(sale_id) FROM customer_sales")
        max_sid = result2[0][0] if result2 and result2[0][0] is not None else 0
        next_sale_id = int(max_sid) + 1
        st.info(f"Sale ID (Auto): **{next_sale_id}**")

        payment_date   = st.date_input("Payment Date", value=datetime.date.today(), key="pi_date")
        amount_paid    = st.text_input("Amount")
        payment_method = st.text_input("Payment Method")

        if st.button("Submit Payment Split"):
            if not all([amount_paid, payment_method]):
                st.warning("Please fill all fields.")
            else:
                mycursor.execute(
                    "INSERT INTO payment_splits (payment_id, sale_id, payment_date, amount_paid, payment_method) VALUES (%s, %s, %s, %s, %s)",
                    (next_payment_id, next_sale_id, payment_date, amount_paid, payment_method)
                )
                mydb.commit()
                st.success("Payment split submitted successfully!")
                st.session_state.action = None


# BRANCH DETAILS SECTION
# ─────────────────────────────────────────
def section_branch_details(branch_id, is_superadmin):
    st.subheader("Branch Details")

    if st.button("View Branch Details"):
        st.session_state.action = "view_branch"

    if st.session_state.action == "view_branch":
        if is_superadmin:
            data = fetch_all("SELECT * FROM branches")
        else:
            data = fetch_all("SELECT * FROM branches WHERE branch_id = %s", (branch_id,))

        if data:
            df = pd.DataFrame(data, columns=[
                "Branch ID", "Branch Name", "branch_admin_name"
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No branch data found.")


# USERS SECTION
# ─────────────────────────────────────────
def section_users(branch_id, is_superadmin):
    st.subheader("User Details")

    if st.button("View Users"):
        st.session_state.action = "view_users"

    if st.session_state.action == "view_users":
        if is_superadmin:
            data = fetch_all("SELECT * FROM users")
        else:
            data = fetch_all("SELECT * FROM users WHERE branch_id = %s", (branch_id,))

        if data:
            df = pd.DataFrame(data, columns=[
                "User ID", "Username", "Password", "Branch ID", "Role", "email"
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No user data found.")


# SQL QUERIES SECTION
# ─────────────────────────────────────────
def section_sql_queries():
    st.subheader("SQL Queries")

    category = st.selectbox("Select Category", [
        "Basic Queries",
        "Aggregation Queries",
        "Join-Based Queries",
        "Financial Tracking Queries"
    ], key="sql_category")

    st.divider()

    if category == "Basic Queries":
        question = st.radio("Select a Query", [
            "1. Retrieve all records from customer_sales",
            "2. Retrieve all records from branches",
            "3. Retrieve all records from payment_splits",
            "4. Display all sales with status = 'Open'",
        ], key="sql_basic")

        if st.button("Run Query"):
            if question == "1. Retrieve all records from customer_sales":
                data = fetch_all("SELECT * FROM customer_sales")
                cols = ["Sale ID", "Branch ID", "Date", "Customer Name", "Mobile Number",
                        "Product Name", "Gross Sales", "Received Amount", "Pending Amount", "Status"]

            elif question == "2. Retrieve all records from branches":
                data = fetch_all("SELECT * FROM branches")
                cols = ["Branch ID", "Branch Name", "Branch Admin Name"]

            elif question == "3. Retrieve all records from payment_splits":
                data = fetch_all("SELECT * FROM payment_splits")
                cols = ["Payment ID", "Sale ID", "Payment Date", "Amount Paid", "Payment Method"]

            elif question == "4. Display all sales with status = 'Open'":
                data = fetch_all("SELECT * FROM customer_sales WHERE status = 'Open'")
                cols = ["Sale ID", "Branch ID", "Date", "Customer Name", "Mobile Number",
                        "Product Name", "Gross Sales", "Received Amount", "Pending Amount", "Status"]

            if data:
                st.dataframe(pd.DataFrame(data, columns=cols), use_container_width=True)
            else:
                st.info("No records found for this query.")

    elif category == "Aggregation Queries":
        question = st.radio("Select a Query", [
            "1. Total gross sales across all branches",
            "2. Total received amount across all sales",
            "3. Total pending amount across all sales",
            "4. Average gross sales per branch",
        ], key="sql_agg")

        if st.button("Run Query"):
            if question == "1. Total gross sales across all branches":
                data = fetch_all("SELECT SUM(gross_sales) AS total_gross_sales FROM customer_sales")
                cols = ["Total Gross Sales"]

            elif question == "2. Total received amount across all sales":
                data = fetch_all("SELECT SUM(received_amount) AS total_received_amount FROM customer_sales")
                cols = ["Total Received Amount"]

            elif question == "3. Total pending amount across all sales":
                data = fetch_all("SELECT SUM(pending_amount) AS total_pending_amount FROM customer_sales")
                cols = ["Total Pending Amount"]

            elif question == "4. Average gross sales per branch":
                data = fetch_all("""
                    SELECT b.branch_name, AVG(cs.gross_sales) AS avg_gross_sales
                    FROM customer_sales cs
                    JOIN branches b ON cs.branch_id = b.branch_id
                    GROUP BY b.branch_name
                """)
                cols = ["Branch Name", "Average Gross Sales"]

            if data:
                st.dataframe(pd.DataFrame(data, columns=cols), use_container_width=True)
            else:
                st.info("No records found for this query.")

    elif category == "Join-Based Queries":
        question = st.radio("Select a Query", [
            "1. Retrieve sales details along with branch name",
            "2. Retrieve sales details along with total payment received",
            "3. Branch-wise total gross sales",
            "4. Display sales along with payment method used",
        ], key="sql_join")

        if st.button("Run Query"):
            if question == "1. Retrieve sales details along with branch name":
                data = fetch_all("""
                    SELECT cs.*, b.branch_name FROM customer_sales cs
                    JOIN branches b ON cs.branch_id = b.branch_id
                """)
                cols = ["Sale ID", "Branch ID", "Date", "Customer Name", "Mobile Number",
                        "Product Name", "Gross Sales", "Received Amount", "Pending Amount", "Status", "Branch Name"]

            elif question == "2. Retrieve sales details along with total payment received":
                data = fetch_all("""
                    SELECT cs.sale_id, cs.name, cs.product_name, cs.gross_sales,
                           SUM(ps.amount_paid) AS total_payment_received
                    FROM customer_sales cs
                    JOIN payment_splits ps ON cs.sale_id = ps.sale_id
                    GROUP BY cs.sale_id, cs.name, cs.product_name, cs.gross_sales
                """)
                cols = ["Sale ID", "Customer Name", "Product Name", "Gross Sales", "Total Payment Received"]

            elif question == "3. Branch-wise total gross sales":
                data = fetch_all("""
                    SELECT b.branch_name, SUM(cs.gross_sales) AS total_gross_sales
                    FROM customer_sales cs
                    JOIN branches b ON cs.branch_id = b.branch_id
                    GROUP BY b.branch_name
                """)
                cols = ["Branch Name", "Total Gross Sales"]

            elif question == "4. Display sales along with payment method used":
                data = fetch_all("""
                    SELECT cs.sale_id, cs.name, cs.product_name, cs.gross_sales,
                           ps.payment_method, ps.amount_paid
                    FROM customer_sales cs
                    JOIN payment_splits ps ON cs.sale_id = ps.sale_id
                """)
                cols = ["Sale ID", "Customer Name", "Product Name", "Gross Sales", "Payment Method", "Amount Paid"]


            if data:
                st.dataframe(pd.DataFrame(data, columns=cols), use_container_width=True)
            else:
                st.info("No records found for this query.")

    elif category == "Financial Tracking Queries":
        question = st.radio("Select a Query", [
            "1. Find sales where pending amount > 5000",
            "2. Retrieve top 3 highest gross sales",
            "3. Find the branch with highest total gross sales",
        ], key="sql_fin")

        if st.button("Run Query"):
            if question == "1. Find sales where pending amount > 5000":
                data = fetch_all("SELECT * FROM customer_sales WHERE pending_amount > 5000")
                cols = ["Sale ID", "Branch ID", "Date", "Customer Name", "Mobile Number",
                        "Product Name", "Gross Sales", "Received Amount", "Pending Amount", "Status"]

            elif question == "2. Retrieve top 3 highest gross sales":
                data = fetch_all("SELECT * FROM customer_sales ORDER BY gross_sales DESC LIMIT 3")
                cols = ["Sale ID", "Branch ID", "Date", "Customer Name", "Mobile Number",
                        "Product Name", "Gross Sales", "Received Amount", "Pending Amount", "Status"]

            elif question == "3. Find the branch with highest total gross sales":
                data = fetch_all("""
                    SELECT b.branch_name, SUM(cs.gross_sales) AS total_gross_sales
                    FROM customer_sales cs
                    JOIN branches b ON cs.branch_id = b.branch_id
                    GROUP BY b.branch_name
                    ORDER BY total_gross_sales DESC
                    LIMIT 1
                """)
                cols = ["Branch Name", "Total Gross Sales"]


            if data:
                st.dataframe(pd.DataFrame(data, columns=cols), use_container_width=True)
            else:
                st.info("No records found for this query.")



# DASHBOARD PAGE
# ─────────────────────────────────────────
def dashboard_page():
    st.set_page_config(page_title="VR-SHOPPING Dashboard", page_icon="🛒", layout="wide")

    user          = st.session_state.user
    branch_id     = st.session_state.branch_id
    is_superadmin = st.session_state.is_superadmin

    col_title, col_logout = st.columns([5, 1])
    with col_title:
        if is_superadmin:
            st.title(" :blue[Super Admin Dashboard] 👑")
            st.caption("Managing all branches")
        else:
            st.title(f"Welcome, {user[1]}! 👋")
            st.caption(f"Branch ID: `{branch_id}`")
    with col_logout:
        st.write(""); st.write("")
        if st.button(" Logout"):
            for k in ["logged_in", "user", "branch_id", "is_superadmin", "action",
                      "prev_section", "selected_summary_branch", "selected_summary_product"]:
                st.session_state[k] = False if k == "logged_in" else None
            st.rerun()

    st.divider()

    st.sidebar.title("Navigation")
    selected = st.sidebar.radio(
        "Go to",
        ["Customer Sales", "Payment Splits", "Branch Details", "Users", "SQL Queries"],
        key="nav_section"
    )

    if st.session_state.prev_section != selected:
        st.session_state.action = None
        st.session_state.selected_summary_branch  = None
        st.session_state.selected_summary_product = None
        st.session_state.prev_section = selected

    if selected == "Customer Sales":
        section_customer_sales(branch_id, is_superadmin)
    elif selected == "Payment Splits":
        section_payment_splits(branch_id, is_superadmin)
    elif selected == "Branch Details":
        section_branch_details(branch_id, is_superadmin)
    elif selected == "Users":
        section_users(branch_id, is_superadmin)
    elif selected == "SQL Queries":
        section_sql_queries()


# APP 

def app():
    if st.session_state.logged_in:
        dashboard_page()
    else:
        login_page()

app()
