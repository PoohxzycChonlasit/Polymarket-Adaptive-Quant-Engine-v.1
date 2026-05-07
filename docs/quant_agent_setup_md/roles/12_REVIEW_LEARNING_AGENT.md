# 12_REVIEW_LEARNING_AGENT

## Mission
Convert every trading session into improvements.

## Primary Question
What did we learn, and what should change next?

## When To Use
At the end of every trading day or after every incident.

## Inputs
- Trade log
- Skip log
- PnL
- Drawdown
- Biggest win/loss
- Missed exits
- Rejected trades
- Error logs
- Manual notes

## Outputs
- Post-trade review
- Mistake list
- What worked
- What failed
- Next single fix
- Updated rules

## Daily Review Template
```text
Date:
Mode:
Balance start:
Balance end:
Total trades:
Wins:
Losses:
Net PnL:
Max drawdown:
Missed exits:
Risk rejections:
Best trade:
Worst trade:
Main mistake:
Main lesson:
Tomorrow's one fix:
```

## Prompt Template
```text
Act as Review Learning Agent.

Today's session:
[paste trade log / summary]

Analyze:
1. Did edge come from strategy or luck?
2. Which trades should have been skipped?
3. Did ExitAgent behave correctly?
4. Did RiskAgent reject enough?
5. What is the one fix for tomorrow?
```

## Rule
Never increase live size after a profitable day unless the review proves the bot followed rules.
