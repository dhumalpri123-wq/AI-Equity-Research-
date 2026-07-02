import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import google.generativeai as genai

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import inch
from datetime import datetime

pdfmetrics.registerFont(
    TTFont("DejaVu", "DejaVuLGCSans.ttf")
)

genai.configure(
    api_key="API KEY "
)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
)

ticker = input(
    "Enter NSE Ticker (Example: INFY): "
).upper()

if not ticker.endswith(".NS"):
    ticker += ".NS"

stock = yf.Ticker(ticker)

info = stock.info

company_name = info.get("longName", ticker.replace(".NS", ""))

sector = info.get("sector", "")
industry = info.get("industry", "")

is_bank = (
    "Bank" in industry
    or "Banks" in industry
)

print(f"Loading {company_name}...\n")
print(f"Sector: {sector}")
print(f"Industry: {industry}")
print(f"Bank Company: {is_bank}")


income = stock.financials

print("\nAvailable Financial Rows:")
print(income.index)

revenue = income.loc["Total Revenue"]
net_income = income.loc["Net Income"]

df = pd.DataFrame({
    "Revenue": revenue,
    "Net Income": net_income
})

df["Profit Margin %"] = (
    df["Net Income"] / df["Revenue"]
) * 100

df["Revenue Growth %"] = (
    df["Revenue"].pct_change(-1)
) * 100

df = df.dropna()

print(df)


first_revenue = df["Revenue"].iloc[-1]
latest_revenue = df["Revenue"].iloc[0]

revenue_growth_total = (
    (latest_revenue - first_revenue)
    / first_revenue
) * 100

avg_margin = df["Profit Margin %"].mean()

roe = info.get("returnOnEquity", 0) * 100

profit_margin = df.iloc[0]["Profit Margin %"]

revenue_growth = df.iloc[0]["Revenue Growth %"]

current_price = info.get("currentPrice", 0)

eps = info.get("trailingEps", 0)

market_cap = info.get("marketCap", 0)

shares_outstanding = info.get("sharesOutstanding", 1)

if revenue_growth_total > 0:
    trend_rating = "POSITIVE"
else:
    trend_rating = "NEGATIVE"

if not is_bank:
    fcf = info.get("freeCashflow", 0)

    if fcf and fcf > 0:

        dcf_growth_rate = 0.08
        discount_rate = 0.10
        terminal_growth = 0.03

        projected_fcfs = []

        for year in range(1, 6):

            future_fcf = fcf * ((1 + dcf_growth_rate) ** year)

            projected_fcfs.append(future_fcf)

        pv_fcfs = 0

        for year, cashflow in enumerate(projected_fcfs, start=1):

            pv_fcfs += cashflow / ((1 + discount_rate) ** year)

        terminal_value = (
            projected_fcfs[-1] * (1 + terminal_growth)
        ) / (discount_rate - terminal_growth)

        pv_terminal = terminal_value / ((1 + discount_rate) ** 5)

        enterprise_value_dcf = pv_fcfs + pv_terminal

        dcf_fair_value = enterprise_value_dcf / shares_outstanding

    else:
        dcf_fair_value = 0
        dcf_upside = 0

else:
    dcf_fair_value = None
    dcf_upside = None


growth_rate = 10

lynch_fair_value = eps * growth_rate

if is_bank:
    target_price = lynch_fair_value
else:
    target_price = (dcf_fair_value + lynch_fair_value) / 2

expected_return = (
    (target_price - current_price)
    / current_price
) * 100


if current_price > 0:

    if not is_bank and dcf_fair_value is not None:
        dcf_upside = (
            (dcf_fair_value - current_price)
            / current_price
        ) * 100
    else:
        dcf_upside = 0

    lynch_upside = (
        (lynch_fair_value - current_price)
        / current_price
    ) * 100

else:
    dcf_upside = 0
    lynch_upside = 0


health_score = 0


if roe > 15:
    roe_status = "PASS"
    health_score += 1
else:
    roe_status = "FAIL"


if profit_margin > 10:
    margin_status = "PASS"
    health_score += 1
else:
    margin_status = "FAIL"


if revenue_growth > 0:
    growth_status = "PASS"
    health_score += 1
else:
    growth_status = "FAIL"


cash = info.get("totalCash", 0)
debt = info.get("totalDebt", 0)

if cash >= debt:
    debt_status = "PASS"
    health_score += 1
else:
    debt_status = "FAIL"

    
investment_score = health_score

if trend_rating == "POSITIVE":
    investment_score += 1

if not is_bank:
    if dcf_fair_value is not None and dcf_fair_value > current_price:
        investment_score += 1

if lynch_fair_value > current_price:
    investment_score += 1


if expected_return >= 15:
    final_rating = "BUY"

elif expected_return >= -10:
    final_rating = "HOLD"

else:
    final_rating = "SELL"
    
dcf_text = (
    f"₹{dcf_fair_value:.2f}"
    if dcf_fair_value is not None
    else "Not Applicable (Bank valuation uses other methods)"
)

master_prompt = f"""
You are a Senior Equity Research Analyst at Morgan Stanley.

Generate a professional institutional-quality Equity Research Report.

Company: {company_name}
Sector: {sector}
Industry: {industry}

Current Price: ₹{current_price:.2f}
Target Price: ₹{target_price:.2f}

Market Cap: ₹{market_cap/1e12:.2f} Trillion

ROE: {roe:.2f}%
Profit Margin: {profit_margin:.2f}%
Revenue Growth: {revenue_growth:.2f}%

PE Ratio: {info.get("trailingPE","N/A")}
EPS: {eps:.2f}

DCF Fair Value: {dcf_text}
Peter Lynch Fair Value: ₹{lynch_fair_value:.2f}

Investment Rating: {final_rating}

Write in a professional analyst tone.

Do NOT use markdown.
Do NOT use bold.
Do NOT write introductions or conclusions.
Only return the sections below.

EXECUTIVE_SUMMARY:
Write exactly 5 concise analyst-style sentences summarizing the company, financial performance, valuation, growth outlook and recommendation.

SWOT:

Strengths:
- 4 bullet points

Weaknesses:
- 4 bullet points

Opportunities:
- 4 bullet points

Threats:
- 4 bullet points

INVESTMENT_THESIS:
Provide exactly 5 professional investment bullet points explaining why an investor should consider the company.

RISKS:
Provide exactly 5 professional investment risk bullet points.

The response must follow this exact structure:

EXECUTIVE_SUMMARY:
...

SWOT:
Strengths:
...
Weaknesses:
...
Opportunities:
...
Threats:
...

INVESTMENT_THESIS:
...

RISKS:
...
"""
master_response = model.generate_content(master_prompt)

report_text = master_response.text


executive_summary = ""
swot = ""
investment_thesis = ""
risks = ""

try:
    executive_summary = report_text.split("EXECUTIVE_SUMMARY:")[1].split("SWOT:")[0].strip()

    swot = report_text.split("SWOT:")[1].split("INVESTMENT_THESIS:")[0].strip()

    investment_thesis = report_text.split("INVESTMENT_THESIS:")[1].split("RISKS:")[0].strip()

    risks = report_text.split("RISKS:")[1].strip()

except Exception:
    executive_summary = report_text
    swot = "Not Available"
    investment_thesis = "Not Available"
    risks = "Not Available"


sector = info.get("sector", "")


peer_map = {

    "Technology": [
        "TCS.NS",
        "INFY.NS",
        "HCLTECH.NS",
        "WIPRO.NS"
    ],

    "Financial Services": [
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "KOTAKBANK.NS",
        "AXISBANK.NS",
        "SBIN.NS"
    ],

    "Energy": [
        "RELIANCE.NS",
        "ONGC.NS",
        "IOC.NS",
        "BPCL.NS"
    ],

    "Automobile": [
        "MARUTI.NS",
        "TATAMOTORS.NS",
        "M&M.NS",
        "BAJAJ-AUTO.NS"
    ],

    "Healthcare": [
        "SUNPHARMA.NS",
        "DRREDDY.NS",
        "CIPLA.NS",
        "DIVISLAB.NS"
    ]

}

peer_tickers = peer_map.get(
    sector,
    [ticker]
)
peer_data = []
peer_pe_list = []

for peer in peer_tickers:

    peer_info = yf.Ticker(peer).info

    pe = peer_info.get("trailingPE", 0)

    if pe:
        peer_pe_list.append(pe)

    peer_data.append([
        peer.replace(".NS",""),
        f"₹{peer_info.get('marketCap',0)/1e12:.2f} T",
        f"{pe:.2f}",
        f"{peer_info.get('returnOnEquity',0)*100:.2f}%"
    ])

average_peer_pe = (
    sum(peer_pe_list) / len(peer_pe_list)
    if peer_pe_list else 0
)
company_pe = info.get("trailingPE",0)

if company_pe < average_peer_pe:
    valuation_status = "UNDERVALUED"
else:
    valuation_status = "OVERVALUED"
    

price = stock.history(period="5y")

plt.figure(figsize=(10,5))

plt.plot(
    price.index,
    price["Close"],
    linewidth=2
)

plt.title(f"{company_name} Stock Price (5 Years)")
plt.xlabel("Date")
plt.ylabel("Price (₹)")
plt.grid(True)

chart_file = f"{ticker.replace('.NS','')}_Price.png"

plt.savefig(chart_file)
plt.close()

plt.figure(figsize=(8,4))

plt.plot(
    df.index.astype(str),
    df["Revenue"]/10000000,
    marker="o"
)

plt.title("Revenue Trend")
plt.ylabel("Revenue (₹ Cr)")
plt.grid(True)

revenue_chart = f"{ticker.replace('.NS','')}_Revenue.png"

plt.savefig(revenue_chart)
plt.close()



plt.figure(figsize=(8,4))

plt.plot(
    df.index.astype(str),
    df["Net Income"]/10000000,
    marker="o"
)

plt.title("Net Income Trend")
plt.ylabel("Net Income (₹ Cr)")
plt.grid(True)

income_chart = f"{ticker.replace('.NS','')}_Income.png"

plt.savefig(income_chart)
plt.close()




pdf = SimpleDocTemplate(
    f"{ticker.replace('.NS','')}_Equity_Research_Report.pdf"
)

styles = getSampleStyleSheet()
today = datetime.today().strftime("%d %B %Y")
for style in styles.byName.values():
    style.fontName = "DejaVu"
    styles["BodyText"].fontName = "DejaVu"
    styles["Normal"].fontName = "DejaVu"
    styles["Heading1"].fontName = "DejaVu"
    styles["Heading2"].fontName = "DejaVu"
    styles["Title"].fontName = "DejaVu"

content = []

content.append(
    Paragraph(
        "AI EQUITY RESEARCH REPORT",
        styles["Title"]
    )
)

content.append(Spacer(1,20))

content.append(
    Paragraph(
        company_name,
        styles["Heading1"]
    )
)

content.append(
    Paragraph(
        f"NSE: {ticker.replace('.NS','')}",
        styles["BodyText"]
    )
)

content.append(
    Paragraph(
        f"Sector: {sector}",
        styles["BodyText"]
    )
)

content.append(
    Paragraph(
        f"Industry: {industry}",
        styles["BodyText"]
    )
)

content.append(Spacer(1,15))

content.append(
    Paragraph(
        f"Current Price : ₹{current_price:.2f}",
        styles["BodyText"]
    )
)

content.append(
    Paragraph(
        f"Target Price : ₹{target_price:.2f}",
        styles["BodyText"]
    )
)

content.append(
    Paragraph(
        f"Expected Return : {expected_return:.2f}%",
        styles["BodyText"]
    )
)

content.append(Spacer(1,15))

content.append(
    Paragraph(
        f"<b>Investment Rating : {final_rating}</b>",
        styles["Heading2"]
    )
)

content.append(Spacer(1,30))

content.append(
    Paragraph(
        "Prepared By",
        styles["Heading2"]
    )
)

content.append(
    Paragraph(
        "Priyraj Dhumal",
        styles["BodyText"]
    )
)

content.append(
    Paragraph(
        f"Report Date : {today}",
        styles["BodyText"]
    )
)

content.append(PageBreak())

content.append(
    Paragraph(
        "Table of Contents",
        styles["Heading1"]
    )
)

toc = [
    "1. Executive Summary",
    "2. SWOT Analysis",
    "3. Investment Thesis",
    "4. Key Risks",
    "5. Company Overview",
    "6. Financial Metrics",
    "7. Valuation Summary",
    "8. Peer Comparison",
    "9. Financial Health Scorecard",
    "10. Charts",
    "11. Investment Recommendation"
]

for item in toc:
    content.append(
        Paragraph(
            item,
            styles["BodyText"]
        )
    )

content.append(PageBreak())


content.append(
    Paragraph(
        "Executive Summary",
        styles["Heading1"]
    )
)

content.append(
    Paragraph(
    executive_summary.replace("\n","<br/>"),
    styles["BodyText"]
)
)

content.append(Spacer(1,20))

content.append(
    Paragraph(
        "SWOT Analysis",
        styles["Heading1"]
    )
)

content.append(
    Paragraph(
        swot.replace("\n","<br/>"),
        styles["BodyText"]
    )
)

content.append(Spacer(1,20))

content.append(
    Paragraph(
        "Investment Thesis",
        styles["Heading1"]
    )
)

content.append(
    Paragraph(
        investment_thesis.replace("\n","<br/>"),
        styles["BodyText"]
    )
)

content.append(Spacer(1,20))

content.append(
    Paragraph(
        "Key Risks",
        styles["Heading1"]
    )
)

content.append(
    Paragraph(
        risks.replace("\n","<br/>"),
        styles["BodyText"]
    )
)

content.append(PageBreak())



content.append(
    Paragraph(
        "Company Overview",
        styles["Heading1"]
    )
)

company_summary = info.get(
    "longBusinessSummary",
    "No company description available."
)

content.append(
    Paragraph(
        company_summary,
        styles["BodyText"]
    )
)



content.append(Spacer(1,20))
content.append(
    Paragraph(
        "Key Financial Metrics",
        styles["Heading1"]
    )
)

metrics = [
    ["Metric","Value"],
    ["Market Cap", f"₹{market_cap/1e12:.2f} Trillion"],
    ["Current Price", f"₹{current_price:.2f}"],
    ["PE Ratio", f"{info.get('trailingPE','N/A')}"],
    ["EPS", f"{eps:.2f}"],
    ["ROE", f"{roe:.2f}%"],
    ["Profit Margin", f"{profit_margin:.2f}%"],
    ["Revenue Growth", f"{revenue_growth:.2f}%"]
]

metric_table = Table(metrics)

metric_table.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0),colors.darkblue),
    ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),

    ('BACKGROUND',(0,1),(0,-1),colors.lightgrey),
    ('BACKGROUND',(1,1),(1,-1),colors.beige),

    ('GRID',(0,0),(-1,-1),1,colors.black),

    ('FONTNAME',(0,0),(-1,-1),'DejaVu'),

    ('ALIGN',(0,0),(-1,-1),'CENTER'),

    ('BOTTOMPADDING',(0,0),(-1,0),10)
]))

content.append(metric_table)

content.append(PageBreak())
content.append(
    Paragraph(
        "Valuation Summary",
        styles["Heading1"]
    )
)

dcf_display = (
    f"₹{dcf_fair_value:.2f}"
    if dcf_fair_value is not None
    else "Not Applicable"
)

dcf_upside_display = (
    f"{dcf_upside:.2f}%"
    if dcf_upside is not None
    else "Not Applicable"
)


valuation_table = Table([
    ["Metric", "Value"],
    ["Current Price", f"₹{current_price:.2f}"],
    ["Target Price", f"₹{target_price:.2f}"],
    ["DCF Fair Value", dcf_display],
    ["Peter Lynch Fair Value", f"₹{lynch_fair_value:.2f}"],
    ["DCF Upside", dcf_upside_display],
    ["Peter Lynch Upside", f"{lynch_upside:.2f}%"],
    ["Final Rating", final_rating]
])

valuation_table.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1F4E78')),
    ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),

    ('BACKGROUND',(0,1),(-1,-1),colors.beige),

    ('GRID',(0,0),(-1,-1),0.75,colors.black),

    ('FONTNAME',(0,0),(-1,-1),'DejaVu'),
    ('FONTNAME',(0,1),(-1,-1),'DejaVu'),

    ('BOTTOMPADDING',(0,0),(-1,0),10),
    ('TOPPADDING',(0,1),(-1,-1),8),
    ('BOTTOMPADDING',(0,1),(-1,-1),8),

    ('ALIGN',(0,0),(-1,-1),'CENTER'),
]))
content.append(
    Paragraph(
        "Valuation Summary",
        styles["Heading2"]
    )
)

content.append(valuation_table)

content.append(Spacer(1,20))

content.append(PageBreak())



content.append(
    Paragraph(
        "Financial Health Scorecard",
        styles["Heading1"]
    )
)

health_table = Table([
    ["Metric", "Status"],
    ["ROE (>15%)", roe_status],
    ["Profit Margin (>10%)", margin_status],
    ["Revenue Growth", growth_status],
    ["Debt Position", debt_status],
    ["Overall Score", f"{health_score}/4"]
])
health_table.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0),colors.darkgreen),
    ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),

    ('BACKGROUND',(0,1),(-1,-1),colors.beige),

    ('GRID',(0,0),(-1,-1),1,colors.black),

    ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),

    ('BOTTOMPADDING',(0,0),(-1,0),10),

    ('ALIGN',(0,0),(-1,-1),'CENTER')
]))

content.append(health_table)

content.append(Spacer(1,20))

content.append(
    Paragraph(
        f"<b>Overall Financial Health:</b> {health_score}/4",
        styles["BodyText"]
    )
)

if health_score == 4:
    health_comment = "Excellent financial position with strong fundamentals."

elif health_score == 3:
    health_comment = "Healthy financial profile with minor concerns."

elif health_score == 2:
    health_comment = "Average financial strength. Investors should monitor key metrics."

else:
    health_comment = "Weak financial profile requiring further analysis."

content.append(
    Paragraph(
        health_comment,
        styles["BodyText"]
    )
)

content.append(PageBreak())

content.append(
    Paragraph(
        "Peer Comparison",
        styles["Heading1"]
    )
)
peer_table_data = [
    ["Company", "Market Cap", "PE", "ROE"]
]

peer_table_data.extend(peer_data)

peer_table = Table(peer_table_data)

peer_table.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0),colors.darkblue),
    ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),

    ('BACKGROUND',(0,1),(-1,-1),colors.beige),

    ('GRID',(0,0),(-1,-1),1,colors.black),

    ('FONTNAME',(0,0),(-1,-1),'DejaVu'),

    ('BOTTOMPADDING',(0,0),(-1,0),10),

    ('ALIGN',(0,0),(-1,-1),'CENTER')
]))
content.append(peer_table)

content.append(Spacer(1,20))

content.append(
    Paragraph(
        "Relative Valuation",
        styles["Heading2"]
    )
)

content.append(
    Paragraph(
        f"Company PE: {company_pe:.2f}",
        styles["BodyText"]
    )
)

content.append(
    Paragraph(
        f"Average Peer PE: {average_peer_pe:.2f}",
        styles["BodyText"]
    )
)

content.append(
    Paragraph(
        f"Valuation Status: {valuation_status}",
        styles["BodyText"]
    )
)

content.append(PageBreak())

content.append(
    Paragraph(
        "Investment Scorecard",
        styles["Heading1"]
    )
)
scorecard = Table([
    ["Category", "Result"],
    ["Financial Health Score", f"{health_score}/4"],
    ["Trend Rating", trend_rating],
    ["Investment Score", f"{investment_score}/6"],
    ["Target Price", f"₹{target_price:.2f}"],
    ["Current Price", f"₹{current_price:.2f}"],
    ["Final Rating", final_rating]
])
scorecard.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0),colors.darkgreen),
    ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),

    ('BACKGROUND',(0,1),(-1,-1),colors.beige),

    ('GRID',(0,0),(-1,-1),1,colors.black),

    ('FONTNAME',(0,0),(-1,-1),'DejaVu'),

    ('BOTTOMPADDING',(0,0),(-1,0),10),

    ('ALIGN',(0,0),(-1,-1),'CENTER')
]))
content.append(scorecard)

content.append(Spacer(1,20))
if final_rating == "BUY":
    analyst_view = (
        "The company demonstrates strong fundamentals, attractive valuation "
        "and favourable long-term growth prospects."
    )

elif final_rating == "HOLD":
    analyst_view = (
        "The company remains fundamentally healthy but appears fairly valued. "
        "Investors should monitor future earnings and growth."
    )

else:
    analyst_view = (
        "Current valuation and financial metrics indicate limited upside. "
        "Investors should remain cautious."
    )

content.append(
    Paragraph(
        "<b>Analyst Opinion</b>",
        styles["Heading2"]
    )
)

content.append(
    Paragraph(
        analyst_view,
        styles["BodyText"]
    )
)
content.append(PageBreak())


content.append(
    Paragraph(
        "Financial Performance",
        styles["Heading1"]
    )
)
financial_table_data = [
    [
        "Year",
        "Revenue (₹ Cr)",
        "Net Income (₹ Cr)",
        "Profit Margin %",
        "Revenue Growth %"
    ]
]

for year in df.index:

    financial_table_data.append([
        str(year.date()),
        f"{df.loc[year,'Revenue']/10000000:,.0f}",
        f"{df.loc[year,'Net Income']/10000000:,.0f}",
        f"{df.loc[year,'Profit Margin %']:.2f}",
        f"{df.loc[year,'Revenue Growth %']:.2f}"
    ])

financial_table = Table(financial_table_data)
financial_table.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0),colors.darkblue),
    ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),

    ('BACKGROUND',(0,1),(-1,-1),colors.beige),

    ('GRID',(0,0),(-1,-1),1,colors.black),

    ('FONTNAME',(0,0),(-1,-1),'DejaVu'),

    ('BOTTOMPADDING',(0,0),(-1,0),10),

    ('ALIGN',(0,0),(-1,-1),'CENTER')
]))
content.append(financial_table)

content.append(Spacer(1,20))
content.append(
    Paragraph(
        "Trend Analysis",
        styles["Heading2"]
    )
)

content.append(
    Paragraph(
        f"Revenue Growth (Multi-Year): {revenue_growth_total:.2f}%",
        styles["BodyText"]
    )
)

content.append(
    Paragraph(
        f"Average Profit Margin: {avg_margin:.2f}%",
        styles["BodyText"]
    )
)

content.append(
    Paragraph(
        f"Overall Trend Rating: {trend_rating}",
        styles["BodyText"]
    )
)

content.append(PageBreak())

content.append(
    Paragraph(
        "5-Year Stock Price",
        styles["Heading1"]
    )
)

content.append(
    Image(
        chart_file,
        width=500,
        height=300
    )
)

content.append(PageBreak())
content.append(
    Paragraph(
        "Revenue Trend",
        styles["Heading1"]
    )
)

content.append(
    Image(
        revenue_chart,
        width=450,
        height=250
    )
)

content.append(PageBreak())
content.append(
    Paragraph(
        "Net Income Trend",
        styles["Heading1"]
    )
)

content.append(
    Image(
        income_chart,
        width=450,
        height=250
    )
)

content.append(PageBreak())
content.append(
    Paragraph(
        "Investment Recommendation",
        styles["Heading1"]
    )
)

rating_table = Table([
    ["FINAL RATING", final_rating]
])

rating_table.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(0,0),colors.darkblue),
    ('TEXTCOLOR',(0,0),(0,0),colors.white),

    ('BACKGROUND',(1,0),(1,0),
        colors.green if final_rating=="BUY"
        else colors.orange if final_rating=="HOLD"
        else colors.red),

    ('TEXTCOLOR',(1,0),(1,0),colors.white),

    ('GRID',(0,0),(-1,-1),1,colors.black),

    ('ALIGN',(0,0),(-1,-1),'CENTER'),

    ('FONTNAME',(0,0),(-1,-1),'DejaVu'),
]))

content.append(rating_table)

content.append(
    Paragraph(
        f"<b>Rating:</b> {final_rating}",
        styles["BodyText"]
    )
)

content.append(
    Paragraph(
        f"<b>Current Price:</b> ₹{current_price:.2f}",
        styles["BodyText"]
    )
)

content.append(
    Paragraph(
        f"<b>Target Price:</b> ₹{target_price:.2f}",
        styles["BodyText"]
    )
)

content.append(
    Paragraph(
        f"<b>Analyst View:</b> {analyst_view}",
        styles["BodyText"]
    )
)

content.append(Spacer(1,20))

content.append(
    Paragraph(
        "Disclaimer",
        styles["Heading1"]
    )
)

disclaimer = """
This report has been generated for educational and informational purposes only.
It does not constitute investment advice, a recommendation to buy or sell
any security, or an offer to provide financial services. Financial data has
been sourced from Yahoo Finance and AI-generated analysis should not be used
as the sole basis for investment decisions. Investors should conduct their
own research or consult a qualified financial advisor before investing.
"""

content.append(
    Paragraph(
        disclaimer,
        styles["BodyText"]
    )
)

def add_page_number(canvas, doc):

    canvas.saveState()

    canvas.setFont("Helvetica",9)

    canvas.drawString(
        inch,
        0.5*inch,
        f"AI Equity Research Report | {company_name}"
    )

    canvas.drawRightString(
        7.5*inch,
        0.5*inch,
        f"Page {doc.page}"
    )

    canvas.restoreState()

pdf.build(
    content,
    onFirstPage=add_page_number,
    onLaterPages=add_page_number
)
print("Equity Research Report Created Succdssfully")