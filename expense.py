import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from enum import Enum
import webbrowser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class TransactionType(Enum):
    INCOME = "income"
    EXPENSE = "expense"

@dataclass
class Transaction:
    id: int
    type: TransactionType
    amount: float
    category: str
    description: str
    date: str
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

class ExpenseTracker:
    def __init__(self, data_file="expense_data.json"):
        self.data_file = data_file
        self.transactions: List[Transaction] = []
        self.budget_limits: Dict[str, float] = {}
        self.categories = {
            'income': ['Salary', 'Business', 'Investment', 'Freelance', 'Other Income'],
            'expense': ['Food', 'Transport', 'Entertainment', 'Utilities', 'Healthcare', 'Shopping', 'Education', 'Other']
        }
        self.load_data()
    
    def load_data(self):
        """Load data from JSON file"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.transactions = [
                    Transaction(
                        id=item['id'],
                        type=TransactionType(item['type']),
                        amount=item['amount'],
                        category=item['category'],
                        description=item['description'],
                        date=item['date'],
                        tags=item.get('tags', [])
                    ) for item in data.get('transactions', [])
                ]
                self.budget_limits = data.get('budget_limits', {})
        except FileNotFoundError:
            self.transactions = []
            self.budget_limits = {}
    
    def save_data(self):
        """Save data to JSON file"""
        data = {
            'transactions': [
                {
                    'id': t.id,
                    'type': t.type.value,
                    'amount': t.amount,
                    'category': t.category,
                    'description': t.description,
                    'date': t.date,
                    'tags': t.tags
                } for t in self.transactions
            ],
            'budget_limits': self.budget_limits
        }
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_next_id(self):
        """Get next available transaction ID"""
        if not self.transactions:
            return 1
        return max(t.id for t in self.transactions) + 1
    
    def add_transaction(self, type: TransactionType, amount: float, category: str, 
                       description: str, tags: List[str] = None):
        """Add a new transaction"""
        if tags is None:
            tags = []
        
        transaction = Transaction(
            id=self.get_next_id(),
            type=type,
            amount=amount,
            category=category,
            description=description,
            date=datetime.datetime.now().strftime("%Y-%m-%d"),
            tags=tags
        )
        
        self.transactions.append(transaction)
        self.save_data()
        return transaction
    
    def set_budget_limit(self, category: str, limit: float):
        """Set budget limit for a category"""
        self.budget_limits[category] = limit
        self.save_data()
    
    def get_category_spending(self, month: Optional[str] = None) -> Dict[str, float]:
        """Get total spending by category for a specific month"""
        spending = {}
        
        for transaction in self.transactions:
            if transaction.type == TransactionType.EXPENSE:
                trans_date = datetime.datetime.strptime(transaction.date, "%Y-%m-%d")
                
                if month is None or trans_date.strftime("%Y-%m") == month:
                    spending[transaction.category] = spending.get(transaction.category, 0) + transaction.amount
        
        return spending
    
    def check_budget_alerts(self, month: Optional[str] = None) -> List[Dict]:
        """Check for budget limit violations"""
        alerts = []
        category_spending = self.get_category_spending(month)
        
        for category, limit in self.budget_limits.items():
            spent = category_spending.get(category, 0)
            if spent > limit:
                alerts.append({
                    'category': category,
                    'limit': limit,
                    'spent': spent,
                    'exceeded_by': spent - limit
                })
        
        return alerts
    
    def calculate_profit_loss(self, month: Optional[str] = None) -> Dict:
        """Calculate profit/loss for a specific period"""
        total_income = 0
        total_expenses = 0
        
        for transaction in self.transactions:
            trans_date = datetime.datetime.strptime(transaction.date, "%Y-%m-%d")
            
            if month is None or trans_date.strftime("%Y-%m") == month:
                if transaction.type == TransactionType.INCOME:
                    total_income += transaction.amount
                else:
                    total_expenses += transaction.amount
        
        net_profit = total_income - total_expenses
        profit_margin = (net_profit / total_income * 100) if total_income > 0 else 0
        
        return {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'profit_margin': profit_margin,
            'is_profitable': net_profit > 0
        }
    
    def get_monthly_summary(self) -> Dict[str, Dict]:
        """Get monthly summary of income and expenses"""
        monthly_data = {}
        
        for transaction in self.transactions:
            month = transaction.date[:7]  # YYYY-MM
            
            if month not in monthly_data:
                monthly_data[month] = {'income': 0, 'expenses': 0}
            
            if transaction.type == TransactionType.INCOME:
                monthly_data[month]['income'] += transaction.amount
            else:
                monthly_data[month]['expenses'] += transaction.amount
        
        return monthly_data
    
    def generate_spending_report(self, month: Optional[str] = None):
        """Generate a visual spending report"""
        category_spending = self.get_category_spending(month)
        
        if not category_spending:
            return None
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        # Pie chart
        ax1.pie(category_spending.values(), labels=category_spending.keys(), autopct='%1.1f%%')
        ax1.set_title('Spending by Category')
        
        # Bar chart
        categories = list(category_spending.keys())
        amounts = list(category_spending.values())
        bars = ax2.bar(categories, amounts, color='skyblue')
        ax2.set_title('Spending Amounts by Category')
        ax2.set_xticklabels(categories, rotation=45)
        
        # Add value labels on bars
        for bar, amount in zip(bars, amounts):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(amounts)*0.01,
                    f'${amount:.2f}', ha='center', va='bottom')
        
        plt.tight_layout()
        return fig
    
    def delete_transaction(self, transaction_id: int):
        """Delete a transaction by ID"""
        self.transactions = [t for t in self.transactions if t.id != transaction_id]
        self.save_data()
    
    def search_transactions(self, query: str, search_type: str = "all") -> List[Transaction]:
        """Search transactions by description or tags"""
        results = []
        
        for transaction in self.transactions:
            if search_type in ["all", "description"] and query.lower() in transaction.description.lower():
                results.append(transaction)
            elif search_type in ["all", "tags"] and any(query.lower() in tag.lower() for tag in transaction.tags):
                results.append(transaction)
        
        return results

class DeveloperContact:
    @staticmethod
    def show_developer_info():
        """Show developer contact information"""
        info_window = tk.Toplevel()
        info_window.title("Developer Contact Information")
        info_window.geometry("500x400")
        info_window.configure(bg='#2c3e50')
        
        # Header
        header_frame = tk.Frame(info_window, bg='#34495e', height=80)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="💻 Developer Information", 
                              font=('Arial', 16, 'bold'), fg='white', bg='#34495e')
        title_label.pack(expand=True)
        
        # Contact Information
        contact_frame = tk.Frame(info_window, bg='#2c3e50')
        contact_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        contacts = [
            ("📧 Gmail", "inscreator728@gmail.com", "mailto:inscreator728@gmail.com"),
            ("📱 WhatsApp", "+91 9944762900", "https://wa.me/+919944762900"),
            ("📱 Telegram", "@LRD_soul", "https://t.me/LRD_soul"),
            ("📷 Instagram", "@LRD_SOUL", "https://instagram.com/lrd_soul"),
            ("💼 LinkedIn", "LRD TECH", "https://www.linkedin.com/in/lrd-tech-470786348/r"),
            ("🐙 GitHub", "ExpenseTracker-Pro", "https://github.com/inscreator728/EXPENSE_TRACKER.git")
        ]
        
        for platform, details, link in contacts:
            contact_item = tk.Frame(contact_frame, bg='#34495e')
            contact_item.pack(fill=tk.X, pady=5, padx=10)
            
            platform_label = tk.Label(contact_item, text=platform, font=('Arial', 12, 'bold'),
                                     fg='#3498db', bg='#34495e', width=12, anchor='w')
            platform_label.pack(side=tk.LEFT, padx=10, pady=8)
            
            details_label = tk.Label(contact_item, text=details, font=('Arial', 11),
                                   fg='white', bg='#34495e', anchor='w')
            details_label.pack(side=tk.LEFT, padx=10, pady=8, fill=tk.X, expand=True)
            
            # Make it clickable
            def make_lambda(url):
                return lambda e: webbrowser.open_new(url)
            
            contact_item.bind('<Button-1>', make_lambda(link))
            platform_label.bind('<Button-1>', make_lambda(link))
            details_label.bind('<Button-1>', make_lambda(link))
            
            # Change cursor on hover
            for widget in [contact_item, platform_label, details_label]:
                widget.configure(cursor="hand2")
        
        # Support message
        support_frame = tk.Frame(info_window, bg='#2c3e50')
        support_frame.pack(fill=tk.X, padx=20, pady=10)
        
        support_text = """💡 For technical support, bug reports, or feature suggestions, 
please contact us through any of the above channels. 
We typically respond within 24 hours."""
        
        support_label = tk.Label(support_frame, text=support_text, font=('Arial', 10),
                               fg='#bdc3c7', bg='#2c3e50', justify=tk.LEFT, wraplength=460)
        support_label.pack(pady=10)
        
        # Close button
        close_btn = tk.Button(info_window, text="Close", font=('Arial', 12, 'bold'),
                            bg='#e74c3c', fg='white', command=info_window.destroy,
                            width=15, height=2)
        close_btn.pack(pady=10)

class ExpenseTrackerGUI:
    def __init__(self, root):
        self.root = root
        self.tracker = ExpenseTracker()
        self.setup_gui()
        self.refresh_dashboard()
    
    def setup_gui(self):
        """Setup the main GUI"""
        self.root.title("💰 Expense Tracker Pro - Financial Management System")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2c3e50')
        
        # Setup styles
        self.setup_styles()
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create main frame
        self.main_frame = tk.Frame(self.root, bg='#2c3e50')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_dashboard_tab()
        self.create_transaction_tab()
        self.create_budget_tab()
        self.create_analysis_tab()
        self.create_reports_tab()
        
        # Bind tab change event
        self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_change)
    
    def setup_styles(self):
        """Configure custom styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('TNotebook', background='#2c3e50')
        style.configure('TNotebook.Tab', background='#34495e', foreground='white')
        style.map('TNotebook.Tab', background=[('selected', '#3498db')])
    
    def create_menu_bar(self):
        """Create menu bar with developer menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Developer menu
        dev_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="👨‍💻 Developer", menu=dev_menu)
        dev_menu.add_command(label="Contact Information", command=DeveloperContact.show_developer_info)
        dev_menu.add_separator()
        dev_menu.add_command(label="About", command=self.show_about)
    
    def show_about(self):
        """Show about information"""
        messagebox.showinfo("About", 
            "Expense Tracker Pro v2.0\n\n"
            "A comprehensive financial management system with:\n"
            "• Expense & Income Tracking\n"
            "• Budget Management\n"
            "• Profit/Loss Analysis\n"
            "• Visual Reports\n"
            "• Real-time Alerts\n\n"
            "Built with Python & Tkinter")
    
    def create_dashboard_tab(self):
        """Create dashboard tab"""
        self.dashboard_tab = tk.Frame(self.notebook, bg='#2c3e50')
        self.notebook.add(self.dashboard_tab, text="📊 Dashboard")
        
        # Dashboard header
        header_frame = tk.Frame(self.dashboard_tab, bg='#34495e', height=80)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="Financial Dashboard", 
                              font=('Arial', 20, 'bold'), fg='white', bg='#34495e')
        title_label.pack(expand=True)
        
        # Quick stats frame
        stats_frame = tk.Frame(self.dashboard_tab, bg='#2c3e50')
        stats_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Create stats cards
        self.income_card = self.create_stat_card(stats_frame, "Total Income", "$0.00", "#27ae60", 0)
        self.expense_card = self.create_stat_card(stats_frame, "Total Expenses", "$0.00", "#e74c3c", 1)
        self.profit_card = self.create_stat_card(stats_frame, "Net Profit", "$0.00", "#3498db", 2)
        self.budget_card = self.create_stat_card(stats_frame, "Budget Alerts", "0", "#f39c12", 3)
        
        # Recent transactions
        trans_frame = tk.Frame(self.dashboard_tab, bg='#2c3e50')
        trans_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        trans_label = tk.Label(trans_frame, text="Recent Transactions", 
                              font=('Arial', 14, 'bold'), fg='white', bg='#2c3e50')
        trans_label.pack(anchor='w')
        
        self.transactions_tree = ttk.Treeview(trans_frame, columns=('Date', 'Type', 'Amount', 'Category', 'Description'), 
                                             show='headings', height=10)
        
        # Configure columns
        for col in self.transactions_tree['columns']:
            self.transactions_tree.heading(col, text=col)
            self.transactions_tree.column(col, width=120)
        
        self.transactions_tree.pack(fill=tk.BOTH, expand=True, pady=5)
    
    def create_stat_card(self, parent, title, value, color, column):
        """Create a statistic card"""
        card = tk.Frame(parent, bg=color, relief=tk.RAISED, bd=2)
        card.grid(row=0, column=column, padx=5, pady=5, sticky='nsew')
        parent.grid_columnconfigure(column, weight=1)
        
        title_label = tk.Label(card, text=title, font=('Arial', 12, 'bold'), 
                              bg=color, fg='white')
        title_label.pack(pady=(10, 5))
        
        value_label = tk.Label(card, text=value, font=('Arial', 16, 'bold'), 
                              bg=color, fg='white')
        value_label.pack(pady=(5, 10))
        
        return value_label
    
    def create_transaction_tab(self):
        """Create transaction management tab"""
        self.transaction_tab = tk.Frame(self.notebook, bg='#2c3e50')
        self.notebook.add(self.transaction_tab, text="💳 Transactions")
        
        # Transaction form
        form_frame = tk.Frame(self.transaction_tab, bg='#34495e', padx=20, pady=20)
        form_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(form_frame, text="Add New Transaction", font=('Arial', 16, 'bold'),
                fg='white', bg='#34495e').grid(row=0, column=0, columnspan=2, pady=10, sticky='w')
        
        # Transaction type
        tk.Label(form_frame, text="Type:", fg='white', bg='#34495e', 
                font=('Arial', 11)).grid(row=1, column=0, sticky='w', pady=5)
        self.trans_type = tk.StringVar(value="expense")
        ttk.Radiobutton(form_frame, text="Income", variable=self.trans_type, 
                       value="income").grid(row=1, column=1, sticky='w', padx=5)
        ttk.Radiobutton(form_frame, text="Expense", variable=self.trans_type, 
                       value="expense").grid(row=1, column=2, sticky='w', padx=5)
        
        # Amount
        tk.Label(form_frame, text="Amount ($):", fg='white', bg='#34495e',
                font=('Arial', 11)).grid(row=2, column=0, sticky='w', pady=5)
        self.amount_var = tk.DoubleVar()
        ttk.Entry(form_frame, textvariable=self.amount_var, font=('Arial', 11)).grid(row=2, column=1, sticky='w', pady=5)
        
        # Category
        tk.Label(form_frame, text="Category:", fg='white', bg='#34495e',
                font=('Arial', 11)).grid(row=3, column=0, sticky='w', pady=5)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(form_frame, textvariable=self.category_var, 
                                          values=self.tracker.categories['expense'], font=('Arial', 11))
        self.category_combo.grid(row=3, column=1, sticky='w', pady=5)
        
        # Description
        tk.Label(form_frame, text="Description:", fg='white', bg='#34495e',
                font=('Arial', 11)).grid(row=4, column=0, sticky='w', pady=5)
        self.desc_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.desc_var, font=('Arial', 11), width=30).grid(row=4, column=1, sticky='w', pady=5)
        
        # Tags
        tk.Label(form_frame, text="Tags (comma separated):", fg='white', bg='#34495e',
                font=('Arial', 11)).grid(row=5, column=0, sticky='w', pady=5)
        self.tags_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.tags_var, font=('Arial', 11), width=30).grid(row=5, column=1, sticky='w', pady=5)
        
        # Buttons
        button_frame = tk.Frame(form_frame, bg='#34495e')
        button_frame.grid(row=6, column=0, columnspan=3, pady=15)
        
        ttk.Button(button_frame, text="Add Transaction", 
                  command=self.add_transaction_gui).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Form", 
                  command=self.clear_form).pack(side=tk.LEFT, padx=5)
        
        # Bind type change to update categories
        self.trans_type.trace('w', self.update_categories)
        
        # Transactions list
        list_frame = tk.Frame(self.transaction_tab, bg='#2c3e50')
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Search frame
        search_frame = tk.Frame(list_frame, bg='#2c3e50')
        search_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Search", 
                  command=self.search_transactions_gui).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Clear Search", 
                  command=self.clear_search).pack(side=tk.LEFT, padx=5)
        
        # Transactions treeview
        self.trans_list_tree = ttk.Treeview(list_frame, 
                                           columns=('ID', 'Date', 'Type', 'Amount', 'Category', 'Description', 'Tags'),
                                           show='headings', height=15)
        
        for col in self.trans_list_tree['columns']:
            self.trans_list_tree.heading(col, text=col)
            self.trans_list_tree.column(col, width=100)
        
        self.trans_list_tree.pack(fill=tk.BOTH, expand=True)
        
        # Delete button
        ttk.Button(list_frame, text="Delete Selected", 
                  command=self.delete_selected_transaction).pack(pady=5)
    
    def create_budget_tab(self):
        """Create budget management tab"""
        self.budget_tab = tk.Frame(self.notebook, bg='#2c3e50')
        self.notebook.add(self.budget_tab, text="💰 Budget")
        
        # Budget setting frame
        budget_set_frame = tk.Frame(self.budget_tab, bg='#34495e', padx=20, pady=20)
        budget_set_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(budget_set_frame, text="Set Budget Limits", font=('Arial', 16, 'bold'),
                fg='white', bg='#34495e').pack(anchor='w', pady=10)
        
        # Category and amount
        input_frame = tk.Frame(budget_set_frame, bg='#34495e')
        input_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(input_frame, text="Category:", fg='white', bg='#34495e',
                font=('Arial', 11)).grid(row=0, column=0, sticky='w', pady=5)
        self.budget_category = tk.StringVar()
        budget_combo = ttk.Combobox(input_frame, textvariable=self.budget_category,
                                   values=self.tracker.categories['expense'], font=('Arial', 11))
        budget_combo.grid(row=0, column=1, sticky='w', padx=10, pady=5)
        
        tk.Label(input_frame, text="Monthly Limit ($):", fg='white', bg='#34495e',
                font=('Arial', 11)).grid(row=0, column=2, sticky='w', pady=5)
        self.budget_amount = tk.DoubleVar()
        ttk.Entry(input_frame, textvariable=self.budget_amount, font=('Arial', 11)).grid(row=0, column=3, sticky='w', padx=10, pady=5)
        
        ttk.Button(input_frame, text="Set Budget", 
                  command=self.set_budget_gui).grid(row=0, column=4, padx=10, pady=5)
        
        # Budget alerts frame
        alerts_frame = tk.Frame(self.budget_tab, bg='#2c3e50')
        alerts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(alerts_frame, text="Budget Alerts", font=('Arial', 14, 'bold'),
                fg='white', bg='#2c3e50').pack(anchor='w', pady=5)
        
        self.alerts_text = scrolledtext.ScrolledText(alerts_frame, height=10, 
                                                    font=('Arial', 10), bg='#34495e', fg='white')
        self.alerts_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Button(alerts_frame, text="Check Alerts", 
                  command=self.check_budget_alerts_gui).pack(pady=5)
    
    def create_analysis_tab(self):
        """Create profit/loss analysis tab"""
        self.analysis_tab = tk.Frame(self.notebook, bg='#2c3e50')
        self.notebook.add(self.analysis_tab, text="📈 Analysis")
        
        # Month selection
        month_frame = tk.Frame(self.analysis_tab, bg='#34495e', padx=20, pady=10)
        month_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(month_frame, text="Select Month:", fg='white', bg='#34495e',
                font=('Arial', 11)).pack(side=tk.LEFT, padx=5)
        
        self.analysis_month = tk.StringVar(value="all")
        month_combo = ttk.Combobox(month_frame, textvariable=self.analysis_month,
                                  values=["all"] + self.get_available_months(), font=('Arial', 11))
        month_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(month_frame, text="Analyze", 
                  command=self.analyze_profit_loss).pack(side=tk.LEFT, padx=10)
        
        # Results frame
        self.results_frame = tk.Frame(self.analysis_tab, bg='#2c3e50')
        self.results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Will be populated by analysis results
    
    def create_reports_tab(self):
        """Create reports tab"""
        self.reports_tab = tk.Frame(self.notebook, bg='#2c3e50')
        self.notebook.add(self.reports_tab, text="📋 Reports")
        
        # Month selection for reports
        report_frame = tk.Frame(self.reports_tab, bg='#34495e', padx=20, pady=10)
        report_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(report_frame, text="Select Month:", fg='white', bg='#34495e',
                font=('Arial', 11)).pack(side=tk.LEFT, padx=5)
        
        self.report_month = tk.StringVar(value="all")
        report_combo = ttk.Combobox(report_frame, textvariable=self.report_month,
                                   values=["all"] + self.get_available_months(), font=('Arial', 11))
        report_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(report_frame, text="Generate Report", 
                  command=self.generate_report_gui).pack(side=tk.LEFT, padx=10)
        
        # Chart frame
        self.chart_frame = tk.Frame(self.reports_tab, bg='#2c3e50')
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def update_categories(self, *args):
        """Update categories based on transaction type"""
        trans_type = self.trans_type.get()
        categories = self.tracker.categories[trans_type]
        self.category_combo['values'] = categories
        if categories:
            self.category_combo.set(categories[0])
    
    def add_transaction_gui(self):
        """Add transaction from GUI"""
        try:
            amount = self.amount_var.get()
            category = self.category_var.get()
            description = self.desc_var.get()
            tags = [tag.strip() for tag in self.tags_var.get().split(',') if tag.strip()]
            
            if amount <= 0:
                messagebox.showerror("Error", "Amount must be positive")
                return
            
            if not category or not description:
                messagebox.showerror("Error", "Category and description are required")
                return
            
            trans_type = TransactionType(self.trans_type.get())
            self.tracker.add_transaction(trans_type, amount, category, description, tags)
            
            messagebox.showinfo("Success", "Transaction added successfully!")
            self.clear_form()
            self.refresh_dashboard()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")
    
    def clear_form(self):
        """Clear transaction form"""
        self.amount_var.set(0)
        self.desc_var.set("")
        self.tags_var.set("")
        self.category_combo.set("")
    
    def search_transactions_gui(self):
        """Search transactions from GUI"""
        query = self.search_var.get()
        if not query:
            self.refresh_transactions_list()
            return
        
        results = self.tracker.search_transactions(query)
        self.update_transactions_tree(results)
    
    def clear_search(self):
        """Clear search and refresh list"""
        self.search_var.set("")
        self.refresh_transactions_list()
    
    def delete_selected_transaction(self):
        """Delete selected transaction"""
        selection = self.trans_list_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a transaction to delete")
            return
        
        item = self.trans_list_tree.item(selection[0])
        trans_id = int(item['values'][0])
        
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this transaction?"):
            self.tracker.delete_transaction(trans_id)
            self.refresh_transactions_list()
            self.refresh_dashboard()
            messagebox.showinfo("Success", "Transaction deleted successfully!")
    
    def set_budget_gui(self):
        """Set budget from GUI"""
        try:
            category = self.budget_category.get()
            limit = self.budget_amount.get()
            
            if not category:
                messagebox.showerror("Error", "Please select a category")
                return
            
            if limit <= 0:
                messagebox.showerror("Error", "Budget limit must be positive")
                return
            
            self.tracker.set_budget_limit(category, limit)
            messagebox.showinfo("Success", f"Budget limit of ${limit:.2f} set for {category}")
            self.budget_category.set("")
            self.budget_amount.set(0)
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")
    
    def check_budget_alerts_gui(self):
        """Check and display budget alerts"""
        alerts = self.tracker.check_budget_alerts()
        
        self.alerts_text.delete(1.0, tk.END)
        
        if not alerts:
            self.alerts_text.insert(tk.END, "✅ All budgets are within limits!\n")
            return
        
        for alert in alerts:
            self.alerts_text.insert(tk.END, 
                f"🚨 BUDGET EXCEEDED: {alert['category']}\n"
                f"   Limit: ${alert['limit']:.2f}\n"
                f"   Spent: ${alert['spent']:.2f}\n"
                f"   Exceeded by: ${alert['exceeded_by']:.2f}\n\n")
    
    def analyze_profit_loss(self):
        """Analyze profit/loss"""
        month = self.analysis_month.get()
        if month == "all":
            month = None
        
        result = self.tracker.calculate_profit_loss(month)
        
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        # Create results display
        period = month if month else "All Time"
        title = tk.Label(self.results_frame, text=f"Profit/Loss Analysis - {period}", 
                        font=('Arial', 16, 'bold'), fg='white', bg='#2c3e50')
        title.pack(pady=10)
        
        # Results in a frame
        results_display = tk.Frame(self.results_frame, bg='#34495e', padx=20, pady=20)
        results_display.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create result labels
        metrics = [
            ("Total Income:", f"${result['total_income']:.2f}", "#27ae60"),
            ("Total Expenses:", f"${result['total_expenses']:.2f}", "#e74c3c"),
            ("Net Profit/Loss:", f"${result['net_profit']:.2f}", 
             "#27ae60" if result['net_profit'] > 0 else "#e74c3c"),
            ("Profit Margin:", f"{result['profit_margin']:.2f}%", 
             "#27ae60" if result['profit_margin'] > 0 else "#e74c3c")
        ]
        
        for i, (label, value, color) in enumerate(metrics):
            row_frame = tk.Frame(results_display, bg='#34495e')
            row_frame.pack(fill=tk.X, pady=8)
            
            tk.Label(row_frame, text=label, font=('Arial', 12, 'bold'),
                    fg='white', bg='#34495e', width=15, anchor='w').pack(side=tk.LEFT)
            tk.Label(row_frame, text=value, font=('Arial', 12, 'bold'),
                    fg=color, bg='#34495e').pack(side=tk.LEFT, padx=10)
        
        # Profitability status
        status_frame = tk.Frame(results_display, bg='#34495e')
        status_frame.pack(pady=20)
        
        if result['is_profitable']:
            status_text = "🎉 PROFITABLE! Your finances are in good shape!"
            status_color = "#27ae60"
        else:
            status_text = "💸 RUNNING AT LOSS! Consider reducing expenses or increasing income."
            status_color = "#e74c3c"
        
        tk.Label(status_frame, text=status_text, font=('Arial', 14, 'bold'),
                fg=status_color, bg='#34495e').pack()
    
    def generate_report_gui(self):
        """Generate visual report"""
        month = self.report_month.get()
        if month == "all":
            month = None
        
        fig = self.tracker.generate_spending_report(month)
        
        # Clear previous chart
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        if fig is None:
            tk.Label(self.chart_frame, text="No spending data available for the selected period.",
                    font=('Arial', 12), fg='white', bg='#2c3e50').pack(expand=True)
            return
        
        # Embed chart in Tkinter
        canvas = FigureCanvasTkAgg(fig, self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def get_available_months(self):
        """Get list of available months from transactions"""
        months = set()
        for transaction in self.tracker.transactions:
            month = transaction.date[:7]
            months.add(month)
        return sorted(months, reverse=True)
    
    def refresh_dashboard(self):
        """Refresh dashboard data"""
        # Update quick stats
        result = self.tracker.calculate_profit_loss()
        alerts = self.tracker.check_budget_alerts()
        
        self.income_card.config(text=f"${result['total_income']:.2f}")
        self.expense_card.config(text=f"${result['total_expenses']:.2f}")
        self.profit_card.config(text=f"${result['net_profit']:.2f}")
        self.profit_card.config(fg="#27ae60" if result['net_profit'] > 0 else "#e74c3c")
        self.budget_card.config(text=str(len(alerts)))
        
        # Update recent transactions
        for item in self.transactions_tree.get_children():
            self.transactions_tree.delete(item)
        
        recent_trans = sorted(self.tracker.transactions, key=lambda x: x.date, reverse=True)[:10]
        for trans in recent_trans:
            self.transactions_tree.insert('', tk.END, values=(
                trans.date,
                "Income" if trans.type == TransactionType.INCOME else "Expense",
                f"${trans.amount:.2f}",
                trans.category,
                trans.description
            ))
    
    def refresh_transactions_list(self):
        """Refresh transactions list"""
        for item in self.trans_list_tree.get_children():
            self.trans_list_tree.delete(item)
        
        for trans in sorted(self.tracker.transactions, key=lambda x: x.date, reverse=True):
            self.trans_list_tree.insert('', tk.END, values=(
                trans.id,
                trans.date,
                "Income" if trans.type == TransactionType.INCOME else "Expense",
                f"${trans.amount:.2f}",
                trans.category,
                trans.description,
                ", ".join(trans.tags)
            ))
    
    def on_tab_change(self, event):
        """Handle tab change events"""
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        
        if current_tab == "📊 Dashboard":
            self.refresh_dashboard()
        elif current_tab == "💳 Transactions":
            self.refresh_transactions_list()
        elif current_tab == "💰 Budget":
            self.check_budget_alerts_gui()

def demo_setup():
    """Set up demo data for testing"""
    tracker = ExpenseTracker("demo_data.json")
    
    # Clear existing data
    tracker.transactions = []
    tracker.budget_limits = {}
    
    # Set budget limits
    tracker.set_budget_limit("Food", 300)
    tracker.set_budget_limit("Transport", 150)
    tracker.set_budget_limit("Entertainment", 200)
    
    # Add sample income
    tracker.add_transaction(TransactionType.INCOME, 5000, "Salary", "Monthly salary", ["salary", "work"])
    tracker.add_transaction(TransactionType.INCOME, 500, "Freelance", "Web development project", ["freelance", "programming"])
    
    # Add sample expenses
    tracker.add_transaction(TransactionType.EXPENSE, 150, "Food", "Groceries", ["groceries", "supermarket"])
    tracker.add_transaction(TransactionType.EXPENSE, 75, "Food", "Restaurant dinner", ["dining", "restaurant"])
    tracker.add_transaction(TransactionType.EXPENSE, 50, "Transport", "Gas", ["car", "fuel"])
    tracker.add_transaction(TransactionType.EXPENSE, 100, "Entertainment", "Movie night", ["movies", "fun"])
    tracker.add_transaction(TransactionType.EXPENSE, 80, "Shopping", "New clothes", ["clothing", "fashion"])
    
    print("✅ Demo data created successfully!")
    return tracker

if __name__ == "__main__":
    # Uncomment the line below to create demo data
    # demo_setup()
    
    # Create and run the GUI application
    root = tk.Tk()
    app = ExpenseTrackerGUI(root)
    root.mainloop()