# Northwind Labs — Incident Log 2026

Every incident that reached severity 2 or above this year, by ID. Each entry records what
happened, what it affected, and what changed afterwards.

## INC-2026-Q1-003 — Atlas scheduling outage

Atlas was unavailable to hospital customers for four hours after a database migration ran
out of disk space. Clinics fell back to paper schedules. The migration runbook now checks
free space before it starts.

## INC-2026-Q2-014 — Reagent contamination

A contaminated reagent batch caused a stomach bug outbreak among participants in the
microbiome trial. Eleven participants were affected; all recovered. Reagent batches are
now tested before use.

## INC-2026-Q3-007 — Unauthorised access attempt

An attacker used a stolen contractor password to try to reach patient records in Atlas.
The second-approval rule blocked the request and no data was exposed. All contractor
accounts were moved to hardware security keys.

## INC-2026-Q3-011 — Invoice export error

A rounding bug in the monthly invoice export overcharged three customers by a total of
$4,180. Finance refunded the difference within a week, and the export now has a
reconciliation check.
