import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF

df = pd.read_csv("data/processed/seller_issues_clean.csv")

total_tickets = df['activity_id'].nunique()

resolved = df[df['status'] == "COMPLETED"].shape[0]

open_tickets = df[df['status'] != "COMPLETED"].shape[0]

resolution_rate = resolved / total_tickets * 100

avg_resolution_time = df['resolution_time_days'].mean()

tickets_by_analyst = df['alias'].value_counts()

avg_time_by_analyst = df.groupby("alias")['resolution_time_days'].mean()

top_categories = df['category_tag'].value_counts().head(5)

tickets_by_analyst.head(5).plot(kind='bar')

plt.title("Top Analysts by Tickets")

plt.tight_layout()

plt.savefig("reports/analyst_tickets.png")

plt.close()

pdf = FPDF()

pdf.add_page()

pdf.set_font("Arial", size=16)

pdf.cell(200,10,"Seller Issue Resolution Report",ln=True,align="C")

pdf.set_font("Arial", size=12)

pdf.ln(10)

pdf.cell(200,10,f"Total Tickets: {total_tickets}",ln=True)

pdf.cell(200,10,f"Resolved Tickets: {resolved}",ln=True)

pdf.cell(200,10,f"Open Tickets: {open_tickets}",ln=True)

pdf.cell(200,10,f"Resolution Rate: {resolution_rate:.2f}%",ln=True)

pdf.cell(200,10,f"Average Resolution Time: {avg_resolution_time:.2f} days",ln=True)

pdf.ln(10)

pdf.image("reports/analyst_tickets.png", w=180)

pdf.output("reports/executive_report.pdf")