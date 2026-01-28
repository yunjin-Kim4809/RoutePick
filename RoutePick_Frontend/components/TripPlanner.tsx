import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, ArrowRight, ArrowLeft, Calendar as CalendarIcon, MapPin, Users, Footprints, Sparkles, Train, Bus, Car, Plus, ChevronLeft, ChevronRight, MoreHorizontal, Github, Navigation, Map, Terminal, Gamepad2, Flag, RefreshCw, Trophy, Timer, Coffee, Camera, Utensils, Music, ShoppingBag, Plane, Pizza, Beer, Star, AlertTriangle } from 'lucide-react';

// --- Loading Animation Assets ---
const ICONS = [
  // 1. Location Pin
  `data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMTAwIDEwMCI+Cgk8cGF0aCBmaWxsPSJjdXJyZW50Q29sb3IiIGQ9Im03MC4zODcgNzBsLTMuODU0IDcuMjQ3bDE4Ljg3LTMuMDg1Yy0zLjgwOC0xLjkxLTguOTYzLTMuMjc1LTE1LjAxNi00LjE2Mm0tNDguNjEgMS41OEMxMy4wMzcgNzMuODg1IDcuNSA3Ny42NjIgNy41IDgzLjI3MmE4LjQgOC40IDAgMCAwIC43NzQgMy40OTdsMzAuMjg1LTQuOTV6TTkxLjc5IDgwbC00Mi4xNSA2Ljg3bDExLjExNiAxMi42NDZDNzkuMDEgOTcuODgxIDkyLjUgOTIuMDUgOTIuNSA4My4yNzJjMC0xLjE3LS4yNTItMi4yNTctLjcxLTMuMjcxbS00OS4yNzIgOC4wNTVsLTI4LjQ4IDQuNjU1QzIxLjU2NiA5Ny4zNzQgMzQuODUzIDEwMCA1MCAxMDBjLjkxOCAwIDEuODE1LS4wMjYgMi43MTktLjA0NXoiIC8+Cgk8cGF0aCBmaWxsPSJjdXJyZW50Q29sb3IiIGQ9Ik01MC4wMDIgMGMtMTYuMyAwLTI5LjY3NCAxMy4zMzMtMjkuNjc0IDI5LjU5NmMwIDYuMjUyIDEuOTg3IDEyLjA3NiA1LjM0MiAxNi44NjVsMTkuMjM0IDMzLjI1bC4wODIuMTA3Yy43NTkuOTkxIDEuNSAxLjc3MyAyLjM3IDIuMzQ4Yy44Ny41NzYgMS45NS45MiAzLjAxLjgxNGMyLjExOC0uMjEyIDMuNDE1LTEuNzA4IDQuNjQ2LTMuMzc2bC4wNjYtLjA4NmwyMS4yMzQtMzYuMTQxbC4wMTItLjAyM2MuNDk4LS45Ljg2Ni0xLjgxNiAxLjE3OC0yLjcwOGEyOS4zIDI5LjMgMCAwIDAgMi4xNy0xMS4wNUM3OS42NzIgMTMuMzMzIDY2LjMwMiAwIDUwLjAwMiAwbTAgMTcuMDQ1YzcuMDcxIDAgMTIuNTkgNS41MDkgMTIuNTkgMTIuNTVjMCA3LjA0My01LjUxOSAxMi41NS0xMi41OSAxMi41NWMtNy4wNzIgMC0xMi41OTQtNS41MDgtMTIuNTk0LTEyLjU1YzAtNy4wNCA1LjUyMy0xMi41NSAxMi41OTQtMTIuNTUiIGNvbG9yPSJjdXJyZW50Q29sb3IiIC8+Cjwvc3ZnPg==`,
  // 2. Route Path
  `data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMTAwIDEwMCI+Cgk8cGF0aCBmaWxsPSJjdXJyZW50Q29sb3IiIGQ9Ik0yMSAzMkM5LjQ1OSAzMiAwIDQxLjQzIDAgNTIuOTRjMCA0LjQ2IDEuNDI0IDguNjA1IDMuODM1IDEyLjAxMmwxNC42MDMgMjUuMjQ0YzIuMDQ1IDIuNjcyIDMuNDA1IDIuMTY1IDUuMTA2LS4xNGwxNi4xMDYtMjcuNDFjLjMyNS0uNTkuNTgtMS4yMTYuODAzLTEuODU2QTIwLjcgMjAuNyAwIDAgMCA0MiA1Mi45NEM0MiA0MS40MyAzMi41NDQgMzIgMjEgMzJtMCA5LjgxMmM2LjIxNiAwIDExLjE2IDQuOTMxIDExLjE2IDExLjEyOVMyNy4yMTUgNjQuMDY4IDIxIDY0LjA2OFM5Ljg0IDU5LjEzOCA5Ljg0IDUyLjk0MVMxNC43ODYgNDEuODEyIDIxIDQxLjgxMiIgLz4KCTxwYXRoIGZpbGw9ImN1cnJlbnRDb2xvciIgZmlsbC1ydWxlPSJldmVub2RkIiBkPSJNODguMjA5IDM3LjQxMmMtMi4yNDcuMDUtNC41LjE0NS02Ljc1Ny4zMTJsLjM0OCA1LjUzMmExMjYgMTI2IDAgMCAxIDYuNTEzLS4zMDN6bS0xMS45NzUuODJjLTMuNDcuNDMxLTYuOTcgMS4wNDUtMTAuNDMgMi4wMzJsMS4zMDMgNS4zNjFjMy4xNDQtLjg5NiA2LjQwMi0xLjQ3NSA5LjcxMS0xLjg4NnpNNjAuNjIzIDQyLjEyYTI0LjUgMjQuNSAwIDAgMC0zLjAwNCAxLjU4M2wtLjAwNC4wMDVsLS4wMDYuMDAyYy0xLjM3NS44NjYtMi44MjQgMS45NjUtNC4wMDcgMy41NjJjLS44NTcgMS4xNTctMS41NTggMi42Mi0xLjcyMiA0LjM1bDUuMDk1LjU2NWMuMDM4LS40MDYuMjQ2LS45NDIuNjItMS40NDZoLjAwMnYtLjAwMmMuNjAzLS44MTYgMS41MDctMS41NTcgMi41ODItMi4yMzVsLjAwNC0uMDAyYTIwIDIwIDAgMCAxIDIuMzg4LTEuMjU2ek01OCA1NC42NTVsLTMuMzAzIDQuMjM1Yy43ODMuNzE2IDEuNjA0IDEuMjY2IDIuMzk3IDEuNzI2bC4wMS4wMDVsLjAxLjAwNmMyLjYzMiAxLjQ5NyA1LjM0NiAyLjM0MiA3Ljg2MiAzLjE0NGwxLjQ0Ni01LjMxOGMtMi41MTUtLjgwMi00Ljg4Ni0xLjU3Ni02LjkxOC0yLjczYy0uNTgyLS4zMzgtMS4wOTItLjY5MS0xLjUwNC0xLjA2OG0xMy4zMzUgNS4yOTRsLTEuNDEyIDUuMzI3bC42NjguMjA4bC44Mi4yNjJjMi43MTQuODgzIDUuMzE0IDEuODI2IDcuNjM4IDMuMTMxbDIuMzU4LTQuOTJjLTIuODEtMS41NzktNS43MjctMi42MTEtOC41MzgtMy41MjVsLS4wMDgtLjAwMmwtLjg0Mi0uMjY5em0xNC44NjcgNy43bC0zLjYyMyAzLjkyYy44NTYuOTI3IDEuNDk3IDIuMDQyIDEuODA5IDMuMTk0bC4wMDIuMDA2bC4wMDIuMDA5Yy4zNzIgMS4zNDUuMzczIDIuOTI3LjA4MiA0LjUyNWw1LjAyNCAxLjA3MmMuNDEtMi4yNTYuNDc2LTQuNzMzLS4xOTgtNy4xNzhjLS41ODctMi4xNjItMS43MDctNC4wNC0zLjA5OC01LjU0OE04Mi43MiA4Mi42NDNhMTIgMTIgMCAwIDEtMS44MjYgMS41NzJoLS4wMDJjLTEuOCAxLjI2Ni0zLjg4OCAyLjIyLTYuMTA2IDMuMDRsMS42NTQgNS4yNDRjMi40MjYtLjg5NyA0LjkxNy0xLjk5NyA3LjI0NS0zLjYzNWwuMDA2LS4wMDVsLjAwMy0uMDAyYTE3IDE3IDAgMCAwIDIuNjM5LTIuMjg3em0tMTIuNjQgNi4wODljLTMuMjEzLjg2NC02LjQ5NyAxLjUyMi05LjgyMSAyLjA4bC43ODQgNS40NzljMy40MjEtLjU3NSA2Ljg1Ni0xLjI2MiAxMC4yNy0yLjE4em0tMTQuODIyIDIuODM2Yy0zLjM0Ni40NTctNi43MS44My0xMC4wODQgMS4xNDhsLjQ0MiA1LjUyMmMzLjQyNi0uMzIyIDYuODU4LS43MDEgMTAuMjg1LTEuMTd6bS0xNS4xNTUgMS41ODNjLTMuMzgxLjI2OC02Ljc3LjQ4Ni0xMC4xNjIuNjdsLjI1NiA1LjUzNmMzLjQyNS0uMTg1IDYuODUzLS40MDYgMTAuMjgtLjY3OHptLTE1LjI1OS45MmMtMi4wMzMuMDk1LTQuMDcxLjE3My02LjExNC4yNDVsLjE2OCA1LjU0MWE1NjAgNTYwIDAgMCAwIDYuMTY2LS4yNDZ6IiBjb2xvcj0iY3VycmVudENvbG9yIiAvPgo8L3N2Zz4=`,
  // 3. Map with Route
  `data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMTAwIDEwMCI+Cgk8cGF0aCBmaWxsPSJjdXJyZW50Q29sb3IiIGZpbGwtcnVsZT0iZXZlbm9kZCIgZD0iTTgzLjExNyAwYy02Ljg4IDAtMTIuNjk4IDQuNzM1LTE0LjM3OSAxMS4wOTJsLTEuODUxLS44NmEyLjUgMi41IDAgMCAwLTIuMTA4IDBMMzQuMTY2IDI0LjQ1M0wzLjU1MyAxMC4yMzNBMi41IDIuNSAwIDAgMCAwIDEyLjV2NzAuMjg3YTIuNSAyLjUgMCAwIDAgMS40NDcgMi4yNjhsMzEuNjY2IDE0LjcwOWEyLjUgMi41IDAgMCAwIDIuMTA4IDBsMzAuNjEzLTE0LjIybDMwLjYxMyAxNC4yMmMxLjY1Ny43NjkgMy41NTMtLjQ0IDMuNTUzLTIuMjY2VjI3LjIxMWEyLjUgMi41IDAgMCAwLTEuNDQ3LTIuMjY4bC0zLjIzLTEuNTAybDEuMDExLTEuNzIyYy4yMy0uNDE3LjQxMy0uODYxLjU3LTEuMzE1QTE0LjcgMTQuNyAwIDAgMCA5OCAxNC44NDJDOTggNi42ODUgOTEuMjk4IDAgODMuMTE3IDBtMCA2Ljk1M2M0LjQwNSAwIDcuOTA4IDMuNDk2IDcuOTA4IDcuODg5YzAgNC4zOTItMy41MDMgNy44ODUtNy45MDggNy44ODVzLTcuOTA4LTMuNDkzLTcuOTA4LTcuODg1YzAtNC4zOTMgMy41MDMtNy44ODkgNy45MDgtNy44ODltLTE2LjE2NiA4LjgyMmwxLjM3Ny42NDFhMTQuNyAxNC43IDAgMCAwIDIuNjI1IDYuOTM4bDEwLjM0OCAxNy44OWMxLjQ1IDEuODk0IDIuNDE0IDEuNTM0IDMuNjE5LS4xbDcuODU3LTEzLjM3M0w5NSAyOC44MDVWOTMuNThMNjcuMzIyIDgwLjcyM2wtLjIyNi0zOS42NzZjLjQwOC4wODguODE1LjE3MyAxLjIyNC4yN2wuOTItMy44OTFhNjQgNjQgMCAwIDAtMi4xNjgtLjQ3M3ptLTIuOTk4LjM1NGwuMTE1IDIwLjMzNmEzNCAzNCAwIDAgMC0zLjExMy0uMjgxbC0uMTQ4IDMuOTk2YzEuMDg4LjA0IDIuMTg1LjE1OCAzLjI4NS4zMThsLjIzIDQwLjIzNGwtMjguNjc2IDEzLjMyM2wtLjM2OS02NC42MDR6TTUgMTYuNDE4bDI3LjI3NSAxMi42N2wuMzcxIDY0Ljk0N0w1IDgxLjE5MXptNTEuNTQzIDIwLjAzOWMtMS4zNzcuMjQ3LTIuNzg2LjY4OC00LjA5OCAxLjQ1MWE5LjkzIDkuOTMgMCAwIDAtMy43MzIgMy44MmwzLjUwMiAxLjkzMmE2IDYgMCAwIDEgMi4yMjYtMi4yODlsLjAwNi0uMDA0bC4wMDYtLjAwNGMuODA3LS40NyAxLjc2OC0uNzg2IDIuNzk3LS45N3ptMTYuNjY2IDIuMDMxbC0xLjEzMyAzLjgzNGMyLjUwMy43NCA0Ljk4MiAxLjU5IDcuNDQ3IDIuNTFsMS4zOTktMy43NDhjLTIuNTMyLS45NDQtNS4xLTEuODI0LTcuNzEzLTIuNTk2bS0yNi4wMDIgNy41OTZsLS4wMy4xNThsLS4wMDMuMDE0Yy0uNDk5IDIuODMxLS40NDYgNS42MTctLjMzNCA4LjI2NWwzLjk5Ni0uMTdjLS4xMDktMi41NjktLjEzMi01LjA1NS4yNzctNy4zODhsLjAyNC0uMTI1em0zLjg2NyAxMi4yMWwtMy45OS4yN2MuMTggMi42NjkuMzcyIDUuMjg1LjM2NSA3Ljg1bDQgLjAxYy4wMDgtMi43Ny0uMTk1LTUuNDc4LS4zNzUtOC4xM20tMy44MjQgMTEuODljLS4xMS45NTMtLjI3NCAxLjg4LS41MTQgMi43N2wtLjAwMi4wMDVsLS4wMDIuMDA4Yy0uMzUgMS4zMzUtLjkzOSAyLjU3MS0xLjc2MSAzLjUzOWwzLjA0NyAyLjU5YzEuMjg4LTEuNTE1IDIuMTA1LTMuMjk4IDIuNTgtNS4xMDJsLjAwMi0uMDA2Yy4zLTEuMTE2LjQ5NS0yLjI0LjYyMy0zLjM1em0tMzMuNzY4IDMuODk4bC0xLjc5NiAzLjU3NGMyLjQ4IDEuMjQ3IDUuMDQ1IDIuMjc4IDcuNjI4IDMuMTdsMS4zMDUtMy43ODFjLTIuNDU1LS44NDctNC44NTItMS44MTUtNy4xMzctMi45NjNtMTAuODM2IDQuMTEzbC0xLjA2NCAzLjg1NmMyLjY0Ni43MzEgNS4zNjYgMS4zMTIgOC4xNDYgMS42MjVsLjQ0Ni0zLjk3NWMtMi41MjEtLjI4My01LjAzNS0uODE3LTcuNTI4LTEuNTA2bTE4LjE0MS4yODJjLTEuOTkyIDEuMDItNC4zOTcgMS4zOTctNi44NyAxLjQyN2wuMDUgNGMyLjgzNC0uMDM0IDUuODY0LS40NDQgOC42NDItMS44Njd6IiBjb2xvcj0iY3VycmVudENvbG9yIiAvPgo8L3N2Zz4=`,
  // 4. Printer
  `data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMTAwIDEwMCI+Cgk8cGF0aCBmaWxsPSJjdXJyZW50Q29sb3IiIGQ9Ik0xNC42NDMgMmEyLjUgMi41IDAgMCAwLTIuNSAyLjV2MTkuNTE0YzEuNjY2LS4wMDMgMy4zMzMtLjAxIDUtLjAxVjdoNTh2MTYuOTkybDUtLjAwMlY0LjVhMi41IDIuNSAwIDAgMC0yLjUtMi41Wk02LjUgMjhBNi40ODYgNi40ODYgMCAwIDAgMCAzNC41djI3QzAgNjUuMTAxIDIuODk5IDY4IDYuNSA2OGg1LjY0M3YyNy41YTIuNSAyLjUgMCAwIDAgMi41IDIuNWg2M2EyLjUgMi41IDAgMCAwIDIuNS0yLjVWNjhIOTMuNWMzLjYwMSAwIDYuNS0yLjg5OSA2LjUtNi41di0yN2MwLTMuNjAxLTIuODk5LTYuNS02LjUtNi41Wm04My40NCA2SDkwYTQgNCAwIDEgMS0uMDYgME0xNy4xNDIgNDhoNHY0MWg1MVY0OGg0djQ1aC01OXptMTEuNzkzIDBINDAuMzdjLS4yMDMuNjM2LS40NzcgMS40MjItMS4xNCAxLjUxOGMyLjI5LjI4NS0uODEgMS4wOTEtMS4xOTYgMi4xMzZjLjc4My4wNCAxLjIxNC0xLjczMyAyLjE1NC0uMzMyYy0uMzI9IDEuMjktLjczNS0xLjEwOC0xLjM1NS43MTFjLTEuNDkzIDEuMDMgMS42NDIgMi43MyAxLjYyMyAyLjc1Yy0uNjU5LTEuNDYzLS41MzQtMi42NC41NDMtMy4wODZjLjYxMi0xLjE9My4wMDEtMi4yNS4zMTYtMy42OTdoMTEuNjg4Yy40My4yOC44NjIuNTcyIDEuMzA3Ljg3MWMxLjQyNSAyLjQxOC0yLjc5NyAzLjI1NC00LjMzMiAyLjg3MWMtMS4wNi4xNDEtMi41MjIuNzA1LTMuMTE2IDEuMTA2Yy0uMzQzIDEuNTQzLjM3OSA0LjM1MS0yLjE2NCA0LjY2NmMtMS45OTkuNjU1LTMuNTgtMy4wMDctNC45NTktMS41NzVjLTIuMDM5IDEuMDIzLS42Ni0zLjAyNi0yLjM3My0uOTA4Yy0uNTc2LS4wODUtMS4wNzYtMi4wNjMtLjY3OC4xMDhjLS41OTguMTI2LTIuMDc1LS42MTktLjUwMS41MTdjLS4yIDEuNDQxLTEuNjMyLS43Ny0yLjM3Ny0uNzM4Yy43MzUtLjcxNiAzLjYzMy0uNzc1IDEuNjU0LTIuMjg1Yy0uMTIzNC4zMjYtMS41OTQtLjcyNi0uMi0uNWMuNzY3LTEuNzcxLTEuMzEzLTEuODc3LTEuODgtMi43OTFjLjIyNCAxLjI3LTEuNjI5LjgwMS0yLjI3OC4xNTZjLjMgMS41OTYgMi42NTcuODY1IDMuNzMgMS43OTdjMS4yNDYgMS40MTUtMi4wODkuMTMtLjcxMiAxLjY4MmMtMi4wNzcuOTM2LTMuNzY1LTEuNzgyLTUuNDY3LTIuOGMtLjYxMi0xLjA5Mi0uMjM1LTEuNTczLjI3OC0yLjE3N200LjQ0OSAxLjM0MmEyIDIgMCAwIDAtLjE0NS0uNDg4YS45LjkgMCAwIDAgLjE0NS40ODhNNjUuOTUgNDhoMS40ODNsMS45OTYgMTAuNzRjLTEuODU2LS45NzItMi41MDgtMy4yNTMtMy41OTQtNC41MzVjMS4zOS0xLjIyLS4zMTEtMy4xMS42NjYtNC42NGMtLjI2LS42My0uNDU4LTEuMTEyLS41NS0xLjU2NW0tNDIuNDE2IDEuMzc1YzEuMzc5Ljc2Mi0xLjI2NiAxLjQxOCAwIDBtMTAuNzA3LjI5Yy0uNzQ4LjI1NC4zODUuMjMgMCAwbS0xMC45NjMuODU1YzEuNjQ3LjMwMyAxLjA4NSAxLjEzNy0uMDU4IDEuMTJjLjAxMi0uMzYyLS4xMS0uNzc0LjA1OC0xLjEybTEwLjg5OS4wMDNjLjk5Ny4zNy0uNDY0LjQ0OCAwIDBtNC45MjYgMS43OTNjMS45ODQuNDc5LTEuNjEyLjI3MiAwIDBtLTcuODcgNC40MTRjMi4wNzMgMS4wMzQtLjU2OCAyLjk2Ni0uNDg2IDEuNTQzYy4zLS41NjMtLjc2Mi0xLjM1LjQ4Ni0xLjU0M20xMC43OTEuMDRjLjQ2LjE2OC0uMzAyLjIyNyAwIDBtLjA5LjI2M3MuNDQ1LjI0Mi0uNDU0Ljc3NyAwIDBtLTE4LjAyMy40MjJjLjcyNC44NjkgMi4yNzYtLjMxMyAyLjE4Ny43MzJjLjk1NC0xIC4zNDIgMS43MTIuOTE2LjAwNGMuNzY2LjEwNC0uNjkgMS4xMzUuNzA1LS4wMTFjMS4yMTgtLjI4Ny40MTMuNTU3IDEuMTguMTg1YzEuMDYgMS43NjMgMi4wODggMy43NiA0LjMyIDMuODRjLS4xMTcgMi4wMzUtMy4yMTkgMi4xNjgtNC40OTIgMS43MjNjLjgyIDEuMjYzLS42MzMuMDgzLS42MTUuMDgyYy0uMjEyIDEuMTk4LTMuMDc3LjE1Ni0zLjQ4MiAyLjAyYy44OTIgMS4yMjYtLjkxMSAxLjU3MS0xLjIyNyAxLjQ5Yy0uODQ2LS4xMTItLjE2OS0zLjg5Ny0uMzktNS4zMjdjLjI5LTEuNDgyLS43MjMtNC4zNDEuODk4LTQuNzM4bS42NS4zNzljLTEuMDI0LjAzNS4xOTEuNzIyIDAgMG0yNC4xOSAyLjk3OGMyLjUyNy41MjMgMy42MSAyLjQyNyA1LjczIDMuNzAyYy42NjkuNjU2IDEuMjgzIDEuOTEgMi4yNDYgMi4wMTdjLjg2OC4zNjIgMi4xOTcgMS4xODQgMy4xMjcuMDIyYy44MyAxLjYyOS0xLjk4IDIuMzEtMi43MjggMS43NDJjLTEuNzc1LjE4OC00LjAxLS44MDQtNi4wNTEtLjYxNWMtLjk2OCAxLjMyNi0yLjk4NyAyLjc1My00LjQ2NyAxLjMxNmMtMS4yMDYuNy0yLjAzIDMuMzcyLTIuODMgNS4xNDNjLS44MDcuMTYxLTMuNzcgMi43NTItMS41MjMgMS4yMTNjMS43ODMtLjkwMy0uNjkgMS4wOS0xLjM5OSAxLjI3NWMtMS4xNTIgMS43ODktMy42NS44NjYtNC45NzggMi4wMjVjLTEuNDY4LjM2My0zLjE5MSAyLjgyLTIuNjUzIDMuNTM0Yy41NjEgMS4xMDUtLjYzOC45ODcuNjQgMS4yMDljLS4wMjQtLjcgMS4wMy40NTYuMzEzLjQ0N2MxLjAyMi42NTggMS4yMzkgMi43MjkuMTE4LjY4MmMtLjc1MS0uODIyLTEuMzYxIDIuOTA2LTIuNTUuNDE4Yy0uMTI3LjE4Mi0xLjI3MyAyLjAzLTEuMjQxLjM0MmMuMDY4LS43MjUtMS4zNyAxLjU0Ny0xLjY2My0uMDMxYy0yLjAzOC0xLjMyMy4zMi0zLjcwNS4yMTUtNS40MTJjLTEuMDE3LTEuNjYzLS4xNzQtMS40MS0uMTAxLTIuOTE4Yy45OS0xLjIyNy43NTYtMi4yNDcuNTktMy45MDZjLTEuNzA3LjUyMS40MzItMS40OS0xLjIzMy0uNDJjLS44MTQtLjEzMi0zLjI1Ni0uMTg2LTEuODEyLTEuMTk0YzEuMTE1IDEuMTE4IDIuNDcyLjA4MSAzLjAzOS0uNTIxYzEuMjc3LS4zMDUtMS40MTEtLjY4Ny0xLjM1LjM1NWMtMi44Ny42NS0xLjg1NS0yLjg5My0uMDk2LTMuNzUyYzEuMTItLjU4NiAxLjU1OC0xLjE0NiAyLjcxLTEuNDY4Yy43MDQuNTA5LS41NzEgMS4zLjg1NS40MDhjMS42NTctLjEwNC0uMDgzIDIuMDQ2LS41NSAyLjY0Yy0uMTg3LTEuNzMyLTIuOTItLjQyNi0yLjE2NS43OTVjMS41MDgtLjY4MyAxLjc0OCAxLjI4NSAyLjgwNS0uNDU5Yy40NjYuOTEyLS4zNTggMS40ODItLjQ0OCAxLjM1NGMxLjUzNSAyLjYzNyAzLjI3LjYzIDMuOTA3LS45N2MxLjk3Ni0uNzE4LTEuNDY4LS43Mi0xLjg3Ny0uNzQzYy0yLjUwNi40NzctLjIyNy0xLjk2My4zLTIuMTljLTEuNTcyLS43NDggMS43NS0xLjEwOCAxLjk2NS0yLjEzNGMuNzAyLjQ4NyAxLjkzOC0xLjQyMiAxLjgwMS4xNDJjLjE3NSAxLjI4My0yLjA3OC0uMjkzLS43MTkgMS4wNjVjLS4xNzQgMS4xODEtLjEuNzM9LjgyLjExOWMtLjAyOC0xLjM4LjkyOC45NTMuNzc4IDEuMzNjMS4xNjIuNTM4IDIuNjM1IDIuNDA1IDQuMzQ2IDIuMjM2Yy0yLjA0NS4zNjYtLjkzIDQuMjYgMS4wOTcgMi43NThjLjM0OS0uODQxLTEuNDMzLTIuMjE1LjU4Ni0xLjQ1Yy41OS0xLjIxNSAyLjA3NS0xLjQ2My45MjgtMy4zNTdjLS4wNy0xLjk0NSAxLjQ3LTMuMjI4IDIuMjctNC40OThjLjU1Ny0uNjM0LjMyMi0yLjAxOSAxLjI0OC0yLjI1Mm0xNC4zNzMgNC4wOTZjMS43MSAxLjUzNSA0LjI2Ni4xIDYuMDM5Ljc4NWMuMzY1IDIuNTQ1LjA5NSA1LjIzMi4xNzQgNy44MzhjLTEuNDIuNTU3LTIuNTgyLS4xNTctMS41OC0xLjY4MWMtLjI3Mi0xLTI2LjY0My0zLjc4LS4xMDYtMy43OWMtLjM3My43MTItMi4xNDUuNDU0LTEuNzc3LS43N2MtMS4wMDctLjM2MS0yLjgzLS45NTctMi43NS0yLjM4Mk00NC4xMjkgNjYuNjZjLjQ3OC40OC0uNDcuNTM4IDAgMG0tLjA0LjQ3M2MuODk3IDEuMTU0LTEuMjE2Ljg5NCAwIDBtLS4wOTMuODU1Yy40NS40NTQtLjgzMyAxLjI3NC0uNTMxIDIuMzgxYy0uOTMyLS40MTkuMDE4LTIuMDMuNTMxLTIuMzhtLS40NDMuMDgyYy4zNDEuMjE4LS42MTYuMTcgMCAwbS0uMzI4LjA5Yy41MjIuMTYyLS40MTkuNDkgMCAwbS0xMy4yMjMuMjk5YzEuMS42NTQtLjk4LjQzIDAgMG0tNi43MDMuMDY0YzEuMDcuNzY1IDEuOTAyLjYzMiAxLjQ1NSAyLjQ3NWMuNjA2LjY1LjE2LTMuMDY0IDEuMzIyLTEuMThjLjYgMS44MjQtMS4wODcgMi4yNDUtMS45OTggMi43ODdjLjU5NC0xLjE2LjE0NS0xLjcwOC0uNzQ4LTEuOTU5Yy0uMTA3LS42OC0uMjc1LTEuNDU2LS4wMzEtMi4xMjNtMjAuODcuMTVjLjQyLjg1Ni0uNTU2LjM2NiAwIDBtLTEuNjYuMTdjLjM4My4yODUtLjYwMy42NCAwIDBtLjMzOS4wODljLjQ1LjMzNy0uNTk2LjE5MyAwIDBtLTEwLjM2OC4zMTZjLjg5Ni4wMS0uMTgyLjYyNyAwIDBtLS4yMjYuNDljLjk2Ni40MzEtLjE4Mi43NzIgMCAwbTYuMDMuMDQ3Yy0xLjExMy40MTMuNjUuMTMgMCAwbS0uODMuNjA0Yy0uNjQyIDEuMDk3LjU2OSAxLjQ3OCAwIDBtLTEzLjg4IDEuNDkyYy42MDYgMS4xNTUtMS4xNTQgMS4xMjQgMCAwbTIuMjIuMDU2Yy43MiAxLjA2NS0xLjYzNS4yNyAwIDBtMS40NjIuNTIyYTEgMSAwIDAgMSAuMzE2LjAzYzEuNDE2LjQ1NS0uNzQzIDEuNjEyLS42MzguOTExYy0xLjE4Ny0uMDYtLjQzMS0uODg4LjMyMi0uOTQxbS0yLjU4Ni4yMzZjLjEwNS0uMDEzLjI0Mi0uMDEuNDIuMDEyYzEuMzg4LjEyNC0uMjAzIDEuMTQzLS42MjcgMS4zOTdjLjMwNS0uNDU1LS41My0xLjMxOC4yMDctMS40MDltLTEuMzQyLjI2NmMuNzEzIDEuMjA5LS43MDMuOTU4IDAgMG01LjU0OS4zMzZjMS40NjkuNDE1LjYwNyAzLjg2Mi0uMjggMi45MzVjLS42NzIgMS4wMzQtMS40NTguMTg1LS4zMTIgMS40MTZjLTEuNTE4IDEuNTE2LTMuNDk0LS43Ny0xLjI4LTEuODY1Yy42MjMtLjg1Ny0xLjQ3LTEuOTE1LjctMS42OTVjLjY4Mi4xMTkuNjk0LS42MDkgMS4xNzItLjc5MW0tMy4yNzcuNTU1Yy45NiAxLjQxNy0uMTc9IDMuNDg3LS45MDkgMi43OThjMS4yOTUgMi4zNjYtMi43MzMtMS4yMTUtLjA1OC0uMjczYy0uNTA2LS42MTYgMS4zNzUtMS41NTQtLjMxMy0xLjI4N2MtLjAyOC0uNTQ4IDEuMjA2LS44OSAxLjI4LTEuMjM4bTQzLjg2My4xODVjLS4wMDYgMS43NS4yMDggNS44MTMtLjExNSA1Ljk5Yy0uODA5LTEuNTE1LTEuMDI0LTIuNjA0LS40NDgtNC4yNDhjMS4yNTctMS4wMjUtLjQ2LTEuMzM4LjU2My0xLjc0Mm0tNDYuMjE3IDEuMDI1YzEuNTQxLjE3NS0uNjI0IDIuMDA2IDAgMG03LjY1IDEuNjIyYy0uNzcuNjkgMS4xNSAxLjA3NiAwIDBtNC44NDQgMi40NDFjLjEtLjAwOC4yMjMtLjAwMi4zNzEuMDI3Yy0uNjcyLjg0Mi0xLjA3NC4wMzItLjM3LS4wMjdtOC4xODYgNC40NDdjLjIwNC43NDQtMS4yNyAxLjA1MyAwIDBtLS41MjYuODU4Yy4zMDguMjItLjMwOC4yMiAwIDBtLTEwLjA0NiAxLjIxM2MuNjI5LjUyMi0uNTg4LjUwOCAwIDBtMi4xMi4wNDNjLjY3LjU5Mi0uNDM4LjM0OCAwIDAiIGNvbG9yPSJjdXJyZW50Q29sb3IiIC8+Cjwvc3ZnPg==`,
];

// Add distinctive colors for each step of the animation
const STEP_COLORS = [
  'from-orange-400 to-pink-500', // Pin - Warm/Excitement
  'from-blue-500 to-cyan-400',   // Route - Logical/Calm
  'from-emerald-400 to-green-500', // Map - Nature/Grounding
  'from-purple-500 to-indigo-500' // Itinerary - Premium/Final
];

const LOADING_STEPS = [
  { label: '목적지 분석 중...', subtext: '숨겨진 명소 탐색', iconIndex: 0 },
  { label: '최적 경로 계산 중...', subtext: '최적 경로 계산', iconIndex: 1 },
  { label: '여정 지도 생성 중...', subtext: '취향에 맞는 루트 생성', iconIndex: 2 },
  { label: '일정 마무리 중...', subtext: '최종 루트 출력', iconIndex: 3 },
];

// --- NEW GAME: Travel Snake (World Tour Edition) ---
// Snake mechanic but with travel theme

const COLS = 20;
const ROWS = 13; // Reverted to 13 to maintain correct aspect ratio
const INITIAL_SPEED = 150;
const MIN_SPEED = 70;

// Food Types with Icons and Points
const TRAVEL_ITEMS = [
    { type: 'pizza', icon: Pizza, color: 'text-orange-500', points: 10 },
    { type: 'sushi', icon: Star, color: 'text-red-500', points: 20 }, // Star acting as premium food
    { type: 'coffee', icon: Coffee, color: 'text-brown-500', points: 5 },
    { type: 'camera', icon: Camera, color: 'text-blue-500', points: 15 },
    { type: 'beer', icon: Beer, color: 'text-yellow-500', points: 10 },
    { type: 'shopping', icon: ShoppingBag, color: 'text-purple-500', points: 25 },
];

const TravelSnakeGame: React.FC = () => {
    const [snake, setSnake] = useState([{x: 5, y: 5}, {x: 4, y: 5}, {x: 3, y: 5}]); // Initial snake
    const [food, setFood] = useState({x: 10, y: 5, item: TRAVEL_ITEMS[0]});
    const [dir, setDir] = useState({x: 1, y: 0}); // Moving right
    const [nextDir, setNextDir] = useState({x: 1, y: 0}); // Buffer for rapid key presses
    const [gameOver, setGameOver] = useState(false);
    const [score, setScore] = useState(0);
    const [highScore, setHighScore] = useState(0);
    const [speed, setSpeed] = useState(INITIAL_SPEED);
    const [isPlaying, setIsPlaying] = useState(false);
    
    // SAFE ZONES logic removed as iPad is now behind the game

    const generateFood = useCallback((currentSnake: {x:number, y:number}[]) => {
        let newFood;
        let valid = false;
        while (!valid) {
            const x = Math.floor(Math.random() * COLS);
            const y = Math.floor(Math.random() * ROWS);
            
            // Check collision with snake
            const onSnake = currentSnake.some(segment => segment.x === x && segment.y === y);
            
            if (!onSnake) {
                const randomItem = TRAVEL_ITEMS[Math.floor(Math.random() * TRAVEL_ITEMS.length)];
                newFood = { x, y, item: randomItem };
                valid = true;
            }
        }
        return newFood!;
    }, []);

    // Game Loop
    useEffect(() => {
        if (gameOver || !isPlaying) return;

        const moveSnake = () => {
            setSnake(prevSnake => {
                const head = prevSnake[0];
                const newHead = { x: head.x + dir.x, y: head.y + dir.y };

                // 1. Check Wall Collision
                if (newHead.x < 0 || newHead.x >= COLS || newHead.y < 0 || newHead.y >= ROWS) {
                    setGameOver(true);
                    return prevSnake;
                }

                // 2. Check Self Collision
                if (prevSnake.some(segment => segment.x === newHead.x && segment.y === newHead.y)) {
                    setGameOver(true);
                    return prevSnake;
                }

                const newSnake = [newHead, ...prevSnake];

                // 3. Check Food
                if (newHead.x === food.x && newHead.y === food.y) {
                    // Eat food
                    setScore(s => s + food.item.points);
                    setSpeed(s => Math.max(MIN_SPEED, s * 0.98)); // Increase speed slightly
                    setFood(generateFood(newSnake));
                    // Don't pop tail (grow)
                } else {
                    // Move normally
                    newSnake.pop();
                }

                return newSnake;
            });
            // Update direction from buffer
            setDir(nextDir);
        };

        const gameInterval = setInterval(moveSnake, speed);
        return () => clearInterval(gameInterval);
    }, [dir, nextDir, food, gameOver, isPlaying, speed, generateFood]);

    // Input Handling
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Prevent scrolling with arrows/space
            if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(e.key)) {
                e.preventDefault();
            }

            if (!isPlaying && e.key === ' ') {
                resetGame();
                return;
            }

            if (gameOver && e.key === ' ') {
                resetGame();
                return;
            }

            switch(e.key) {
                case 'ArrowUp': 
                    if (dir.y === 0) setNextDir({x: 0, y: -1}); 
                    break;
                case 'ArrowDown': 
                    if (dir.y === 0) setNextDir({x: 0, y: 1}); 
                    break;
                case 'ArrowLeft': 
                    if (dir.x === 0) setNextDir({x: -1, y: 0}); 
                    break;
                case 'ArrowRight': 
                    if (dir.x === 0) setNextDir({x: 1, y: 0}); 
                    break;
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [dir, isPlaying, gameOver]);

    const resetGame = () => {
        setSnake([{x: 5, y: 5}, {x: 4, y: 5}, {x: 3, y: 5}]);
        setDir({x: 1, y: 0});
        setNextDir({x: 1, y: 0});
        setScore(0);
        setSpeed(INITIAL_SPEED);
        setGameOver(false);
        setIsPlaying(true);
        if (score > highScore) setHighScore(score);
        setFood(generateFood([{x: 5, y: 5}, {x: 4, y: 5}, {x: 3, y: 5}]));
    };

    return (
        <div className="w-full h-full relative bg-gray-50 flex flex-col items-center justify-start select-none font-mono">
            
            {/* --- GAME HEADER (Score & Status) --- */}
            {/* INCREASED TOP MARGIN FROM mt-16 TO mt-32 TO AVOID NOTIFICATION OVERLAP */}
            <div className="w-full px-8 mt-32 flex justify-between items-center z-10 transition-all duration-300">
                <div className="flex flex-col">
                    <span className="text-[10px] uppercase text-gray-400 font-bold tracking-widest">Score</span>
                    <span className="text-2xl font-black text-black">{score}</span>
                </div>
                
                {!isPlaying && !gameOver && (
                    <div className="animate-pulse text-sm font-bold bg-black text-white px-4 py-1 rounded-full">
                        PRESS SPACE TO START
                    </div>
                )}
                
                <div className="flex flex-col items-end">
                    <span className="text-[10px] uppercase text-gray-400 font-bold tracking-widest">Best</span>
                    <span className="text-xl font-bold text-gray-500">{Math.max(score, highScore)}</span>
                </div>
            </div>

            {/* --- GAME GRID --- */}
            <div 
                className="relative mt-4 bg-white border-2 border-gray-200 rounded-lg shadow-sm overflow-hidden"
                style={{
                    width: '90%',
                    aspectRatio: `${COLS}/${ROWS}`,
                    display: 'grid',
                    gridTemplateColumns: `repeat(${COLS}, 1fr)`,
                    gridTemplateRows: `repeat(${ROWS}, 1fr)`
                }}
            >
                {/* Overlay: Game Over */}
                {gameOver && (
                    <div className="absolute inset-0 z-20 bg-black/50 backdrop-blur-sm flex flex-col items-center justify-center text-white">
                        <Trophy className="w-12 h-12 mb-2 text-yellow-400" />
                        <h3 className="text-2xl font-bold mb-1">Game Over</h3>
                        <p className="text-sm opacity-80 mb-4">Final Score: {score}</p>
                        <button 
                            onClick={resetGame}
                            className="px-6 py-2 bg-white text-black font-bold rounded-full hover:bg-gray-200 transition-colors"
                        >
                            Try Again
                        </button>
                    </div>
                )}

                {/* Grid Cells */}
                {Array.from({ length: ROWS * COLS }).map((_, i) => {
                    const x = i % COLS;
                    const y = Math.floor(i / COLS);
                    
                    const isSnakeHead = snake[0].x === x && snake[0].y === y;
                    const isSnakeBody = snake.slice(1).some(s => s.x === x && s.y === y);
                    const isFood = food.x === x && food.y === y;

                    return (
                        <div key={i} className="relative flex items-center justify-center">
                            {/* Grid Lines (Subtle) */}
                            <div className="absolute inset-0 border-[0.5px] border-gray-50"></div>

                            {/* Food */}
                            {isFood && (
                                <food.item.icon className={`w-3/4 h-3/4 ${food.item.color} animate-bounce`} />
                            )}

                            {/* Snake Body */}
                            {isSnakeBody && (
                                <div className="w-full h-full bg-black rounded-sm scale-90"></div>
                            )}

                            {/* Snake Head */}
                            {isSnakeHead && (
                                <div className="w-full h-full bg-black rounded-sm flex items-center justify-center z-10 relative">
                                    <Plane className={`w-3/4 h-3/4 text-white transform transition-transform duration-100
                                        ${dir.x === 1 ? 'rotate-90' : ''}
                                        ${dir.x === -1 ? '-rotate-90' : ''}
                                        ${dir.y === 1 ? 'rotate-180' : ''}
                                        ${dir.y === -1 ? 'rotate-0' : ''}
                                    `} />
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Controls Hint - Translated to Korean and styled with sans-serif */}
            <div className="mt-4 flex gap-4 text-[10px] font-bold text-gray-400 uppercase tracking-widest font-sans">
                <span className="flex items-center gap-1"><span className="p-1 border rounded bg-white">방향키</span> 이동</span>
                <span className="flex items-center gap-1"><span className="p-1 border rounded bg-white">스페이스바</span> 재시작</span>
            </div>
        </div>
    );
};
// --- END NEW GAME ---


interface TripPlannerProps {
  isOpen: boolean;
  onClose: () => void;
}

interface FormData {
  theme: string;
  location: string;
  groupSize: string;
  startDate: string;
  endDate: string;
  visitTime: string; // '오전' | '오후' | '저녁' | '하루종일' | '기타(직접 입력)' 등 표시용
  transportation: string[];
  customTransport: string; // Store custom transport input separately
  budget: string; // 예산 정보
}

const steps = [
  { id: 'theme', title: '여행 테마', question: '어떤 여행을 계획하고 계신가요?' },
  { id: 'location', title: '지역', question: '어디로 떠나시나요?' },
  { id: 'groupSize', title: '여행 인원', question: '함께하는 인원은 몇 명인가요?' },
  { id: 'date', title: '방문 일자', question: '일정이 어떻게 되시나요?' },
  { id: 'visitTime', title: '방문 시간', question: '선호하는 시간대가 있으신가요?' },
  { id: 'transportation', title: '이동 수단', question: '주로 어떻게 이동하시나요?' },
  { id: 'budget', title: '예산', question: '예상 예산이 얼마인가요?' },
  { id: 'review', title: '입력 확인', question: '이대로 일정을 생성할까요?' },
];

// 랜덤 테마 후보
const RANDOM_THEMES: string[] = [
  '비 오는 날 실내 데이트 여행',
  '가벼운 산책과 카페 위주의 하루',
  '사진 많이 찍는 감성 여행',
  '조용히 힐링하는 휴식 여행',
  '야경 보면서 걷는 저녁 산책 여행',
  '맛있는 음식 위주의 먹방 여행',
  '커플을 위한 로맨틱 산책 여행',
  '가족과 함께하는 여유로운 당일치기 여행',
  '친구들과 가볍게 즐기는 소도시 여행',
  '전통과 분위기를 함께 느끼는 문화 탐방 여행',
  '드라이브와 카페를 함께 즐기는 데이트 여행',
  '반려동물과 함께하는 산책 위주 여행',
  '아이들과 놀이 중심의 가족 여행',
  '조용한 서점과 카페를 도는 혼자만의 취향 여행',
  '야시장과 길거리 음식을 즐기는 야간 여행',
  '핫플 대신 숨은 로컬 맛집을 찾는 로컬 탐방 여행',
  '전시와 공연을 중심으로 한 문화 예술 여행',
  '바다 보면서 산책하는 여유로운 힐링 여행',
  '호캉스와 주변 산책을 가볍게 즐기는 휴식 여행',
  '한적한 카페에서 공부·작업하는 워케이션 느낌 여행',
  '사진 스팟 위주로 인생샷을 남기는 여행',
  '새로운 동네를 탐험하는 동네 산책 여행',
  '야외 피크닉과 산책을 함께 즐기는 감성 여행',
  '밤늦게까지 즐기는 감성 바·라운지 위주 여행',
  '체험 활동(공방 등)을 중심으로 한 액티비티 여행',
  '계절 감성을 느끼는 계절 한정 테마 여행',
  '아날로그 감성을 찾아 떠나는 레코드숍과 빈티지 소품숍 여행',
  '갓 구운 빵 냄새를 따라가는 빵순이·빵돌이를 위한 빵지순례 여행',
  '환경을 생각하는 비건 맛집과 제로웨이스트 숍 중심의 가치 소비 여행',
  '일몰 시간에 맞춰 황홀한 노을을 감상하는 낭만적인 선셋 산책 여행',
  '루프탑에서 도심의 야경을 한눈에 담으며 즐기는 힙한 감성 여행',
  '가벼운 산행 후 숲속에서 즐기는 건강한 보양식과 맑은 공기 여행',
  '꽃 시장과 식물 카페를 돌며 마음을 정화하는 싱그러운 가드닝 여행',
  '오래된 골목길 속 숨겨진 이야기와 전통을 찾아가는 역사 산책 여행',
  '미술관 옆 예쁜 길을 따라 걷는 여유로운 아트 갤러리 투어',
  '복잡한 도심을 벗어나 강변 공원에서 책 한 권과 함께하는 물멍 피크닉 여행'
];

const TripPlanner: React.FC<TripPlannerProps> = ({ isOpen, onClose }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  
  const [gameMode, setGameMode] = useState(false); // Toggle between Map and Game

  // Custom states for UI logic
  const [isGroupSizeOther, setIsGroupSizeOther] = useState(false);
  const [isTransportOther, setIsTransportOther] = useState(false);
  const [isVisitTimeCustom, setIsVisitTimeCustom] = useState(false);
  const [customStartTime, setCustomStartTime] = useState<{ hour: number; minute: number }>({ hour: 8, minute: 0 });
  const [customEndTime, setCustomEndTime] = useState<{ hour: number; minute: number }>({ hour: 12, minute: 0 });
  
  // Loading Animation State
  const [activeLoadingStep, setActiveLoadingStep] = useState(0);
  
  // 2. 알림창 제어를 위한 State 추가 
  const [currentLog, setCurrentLog] = useState("여행 생성 요청 중..."); // 현재 표시할 메시지
  const [showLog, setShowLog] = useState(false); // 알림창 보임/숨김 여부
  const lastLogRef = useRef(""); // 중복 메시지 깜빡임 방지용

  // Calendar State
  const [currentMonth, setCurrentMonth] = useState(new Date());

  const [formData, setFormData] = useState<FormData>({
    theme: '',
    location: '',
    groupSize: '',
    startDate: '',
    endDate: '',
    visitTime: '',
    transportation: [],
    customTransport: '',
    budget: '',
  });

  // Reset state when opened
  useEffect(() => {
    if (isOpen) {
      setCurrentStep(0);
      setIsLoading(false);
      setIsCompleted(false);
      setIsGroupSizeOther(false);
      setIsTransportOther(false);
      setIsVisitTimeCustom(false);
      setCustomStartTime({ hour: 8, minute: 0 });
      setCustomEndTime({ hour: 12, minute: 0 });
      setFormData({
        theme: '',
        location: '',
        groupSize: '',
        startDate: '',
        endDate: '',
        visitTime: '',
        transportation: [],
        customTransport: '',
        budget: '',
      });
      setCurrentMonth(new Date());
    }
  }, [isOpen]);


  // Loading Animation Timer
  useEffect(() => {
    if (isLoading) {
      const interval = setInterval(() => {
        setActiveLoadingStep((prev) => (prev + 1) % LOADING_STEPS.length);
      }, 5000); // 5 seconds per step as requested
      return () => clearInterval(interval);
    }
  }, [isLoading]);

  // Enter 키로 다음 단계 이동 (review 단계에서만)
  useEffect(() => {
    if (!isOpen) return;
    
    const handleKeyDown = (e: KeyboardEvent) => {
      // review 단계에서만 Enter 키로 제출
      if (currentStep === steps.length - 1 && e.key === 'Enter') {
        handleNext();
      }
    };

    if (currentStep === steps.length - 1) {
      window.addEventListener('keydown', handleKeyDown);
      return () => {
        window.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [isOpen, currentStep]);

const handleNext = async () => {
    // STEP 5(visitTime)에서 커스텀 시간 선택 시 유효성 검증
    const currentStepId = steps[currentStep]?.id;
    if (
      currentStepId === 'visitTime' &&
      isVisitTimeCustom &&
      formData.startDate &&
      formData.endDate &&
      formData.startDate === formData.endDate
    ) {
      const startTotalMinutes = customStartTime.hour * 60 + customStartTime.minute;
      const endTotalMinutes = customEndTime.hour * 60 + customEndTime.minute;

      if (endTotalMinutes <= startTotalMinutes) {
        alert('같은 날 여행을 선택하셨을 때는 종료 시간이 시작 시간보다 뒤여야 합니다.');
        return;
      }
    }

    if (currentStep < steps.length - 1) {
      setCurrentStep(prev => prev + 1);
    } else {
        // 마지막 단계: 로딩 시작
        setIsLoading(true);
        setShowLog(true); // 로딩 시작되자마자 알림창 띄우기
      try {
        // 1. Flask 서버에 데이터 전송
        const response = await fetch('http://127.0.0.1:5000/api/create-trip', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(formData),
        });

        if (!response.ok) {
          throw new Error('서버에서 오류가 발생했습니다.');
        }

        const data = await response.json();
        const { taskId } = data;

        // 2. 상태 확인 폴링 (1초 간격으로 변경하여 반응 속도 향상)
        const pollStatus = setInterval(async () => {
          try {
            const statusResponse = await fetch(`http://127.0.0.1:5000/status/${taskId}`);
            const statusData = await statusResponse.json();
            if (statusData.message && statusData.message !== lastLogRef.current) {
                lastLogRef.current = statusData.message;
                
                setShowLog(false); // 1. 살짝 숨기고 (애니메이션)
                setTimeout(() => {
                    setCurrentLog(statusData.message); // 2. 내용 바꾸고
                    setShowLog(true); // 3. 다시 표시
                }, 200);
            }

            if (statusData.done) {
              clearInterval(pollStatus); // 폴링 중단
              setIsLoading(false); // 로딩 끝 

              if (statusData.success) {
                // 성공 시 이동
                window.location.href = `http://127.0.0.1:5000/chat-map/${taskId}`;
              } else {
                alert(`여행 생성 실패: ${statusData.error || '알 수 없는 오류'}`);
                onClose();
              }
            }
          } catch (error) {
            // 에러 발생 시에도 계속 시도 (네트워크 일시적 끊김 대비)
            console.warn("Polling error, retrying...", error);
          }
        }, 1000); // 1초마다 확인

      } catch (error) {
        setIsLoading(false);
        alert('여행 계획 생성 요청에 실패했습니다.');
        console.error("API Error:", error);
      }
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  };

  // Transportation Toggle Logic
  const toggleTransport = (mode: string) => {
    if (mode === '기타') {
        setIsTransportOther(!isTransportOther);
        // Clear custom transport text if unchecking
        if (isTransportOther) {
             setFormData(prev => ({...prev, customTransport: ''}));
        }
        return;
    }

    setFormData(prev => {
      const exists = prev.transportation.includes(mode);
      return {
        ...prev,
        transportation: exists 
          ? prev.transportation.filter(t => t !== mode)
          : [...prev.transportation, mode]
      };
    });
  };

  // Group Size Logic
  const handleGroupSizeSelect = (value: string) => {
      if (value === '4명+') {
          setIsGroupSizeOther(true);
          setFormData(prev => ({ ...prev, groupSize: '' })); // Clear specific number to force input
      } else {
          setIsGroupSizeOther(false);
          setFormData(prev => ({ ...prev, groupSize: value }));
      }
  };

  // --- Calendar Logic ---
  const getDaysInMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  };
  
  const getFirstDayOfMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
  };

  const handleDateClick = (day: number) => {
    const clickedDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);
    // Format to YYYY-MM-DD (local time)
    const offset = clickedDate.getTimezoneOffset() * 60000;
    const dateStr = new Date(clickedDate.getTime() - offset).toISOString().split('T')[0];

    if (!formData.startDate || (formData.startDate && formData.endDate)) {
        // Start new selection
        setFormData(prev => ({ ...prev, startDate: dateStr, endDate: '' }));
    } else {
        // Select end date
        if (new Date(dateStr) < new Date(formData.startDate)) {
            // If clicked before start date, make it new start date
             setFormData(prev => ({ ...prev, startDate: dateStr, endDate: '' }));
        } else {
             setFormData(prev => ({ ...prev, endDate: dateStr }));
        }
    }
  };

  const changeMonth = (delta: number) => {
      const newDate = new Date(currentMonth);
      newDate.setMonth(newDate.getMonth() + delta);
      setCurrentMonth(newDate);
  };

  const renderCalendar = () => {
    const daysInMonth = getDaysInMonth(currentMonth);
    const firstDay = getFirstDayOfMonth(currentMonth);
    const days = [];

    // Empty cells for previous month
    for (let i = 0; i < firstDay; i++) {
        days.push(<div key={`empty-${i}`} className="h-10 w-10"></div>);
    }

    // Days
    for (let day = 1; day <= daysInMonth; day++) {
        const date = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);
        const offset = date.getTimezoneOffset() * 60000;
        const dateStr = new Date(date.getTime() - offset).toISOString().split('T')[0];
        
        let isSelected = false;
        let isRange = false;
        let isStart = false;
        let isEnd = false;

        if (formData.startDate === dateStr) {
            isSelected = true;
            isStart = true;
        }
        if (formData.endDate === dateStr) {
            isSelected = true;
            isEnd = true;
        }
        if (formData.startDate && formData.endDate) {
            if (dateStr > formData.startDate && dateStr < formData.endDate) {
                isRange = true;
            }
        }

        days.push(
            <button
                key={day}
                onClick={() => handleDateClick(day)}
                className={`h-10 w-10 flex items-center justify-center rounded-full text-sm transition-all
                    ${isSelected ? 'bg-black text-white font-bold' : 'hover:bg-gray-100'}
                    ${isRange ? 'bg-gray-100 text-black rounded-none w-full' : ''}
                    ${isStart && formData.endDate ? 'rounded-r-none' : ''}
                    ${isEnd && formData.startDate ? 'rounded-l-none' : ''}
                `}
            >
                {day}
            </button>
        );
    }
    return days;
  };

  if (!isOpen) return null;

  // --------------------------------------------------------------------------
  // LOADING
  // --------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div className="fixed inset-0 z-[60] bg-gray-50 flex flex-col lg:flex-row items-center justify-center p-6 lg:p-24 gap-12 lg:gap-24 overflow-hidden">
        
        {/* Left: Status Text */}
        <div className="flex-1 max-w-xl space-y-8 animate-fade-in-up z-10 text-left">
            <h2 className="text-4xl md:text-6xl font-serif font-bold text-black leading-[1.3] mb-3">
              여행 경로를<br />
              <span className="text-gray-400 font-light">설계하는 중입니다</span>
            </h2>

            <p className="text-xl md:text-2xl text-gray-500 font-medium animate-pulse">
                AI가 최적의 루트를 분석하고 있습니다
            </p>
            
            <div className="space-y-6 pt-8">
              <div className="flex items-center gap-4">
                <div className="relative">
                    <div className="w-3 h-3 bg-black rounded-full animate-ping absolute opacity-75"></div>
                    <div className="w-3 h-3 bg-black rounded-full relative"></div>
                </div>
                <p className="text-sm font-bold tracking-[0.2em] uppercase text-gray-800">취향 분석</p>
              </div>
              <div className="flex items-center gap-4">
                 <div className="relative">
                    <div className="w-3 h-3 bg-black rounded-full animate-ping absolute opacity-75 delay-150"></div>
                    <div className="w-3 h-3 bg-black rounded-full relative"></div>
                </div>
                <p className="text-sm font-bold tracking-[0.2em] uppercase text-gray-800">경로 최적화</p>
              </div>
              <div className="flex items-center gap-4">
                 <div className="relative">
                    <div className="w-3 h-3 bg-black rounded-full animate-ping absolute opacity-75 delay-300"></div>
                    <div className="w-3 h-3 bg-black rounded-full relative"></div>
                </div>
                <p className="text-sm font-bold tracking-[0.2em] uppercase text-gray-800">주어진 개인 조건 반영</p>
              </div>
            </div>
        </div>

        {/* Right: The Monitor/Device Screen */}
        <div className="flex-1 w-full max-w-3xl animate-fade-in-up delay-200 perspective-1000 relative lg:-translate-x-32 lg:-translate-y-24">
             
             {/* 1. MAIN MONITOR (Spline Map) */}
             {/* Dynamic z-index based on gameMode */}
             <div className={`relative aspect-[4/3] w-full bg-white rounded-[2rem] shadow-[0_30px_60px_-15px_rgba(0,0,0,0.15)] overflow-hidden border-[6px] border-white ring-1 ring-gray-900/5 transition-all duration-700 ease-out ${gameMode ? 'z-30 scale-100' : 'z-10 scale-[0.98]'}`}>
                
                {/* Window Controls */}
                <div className="absolute top-0 left-0 right-0 h-10 bg-gray-50/90 backdrop-blur-sm border-b border-gray-100 flex items-center px-5 gap-2 z-10 justify-between">
                   <div className="flex gap-2">
                        <div className="w-3 h-3 rounded-full bg-[#FF5F56] shadow-sm"></div>
                        <div className="w-3 h-3 rounded-full bg-[#FFBD2E] shadow-sm"></div>
                        <div className="w-3 h-3 rounded-full bg-[#27C93F] shadow-sm"></div>
                   </div>

                   {/* Address Bar / Mode Switcher */}
                   <div className="flex-1 mx-4 h-6 bg-gray-200/50 rounded-md flex items-center justify-between px-1">
                        <button 
                            onClick={() => setGameMode(false)}
                            className={`flex-1 flex items-center justify-center rounded text-[10px] font-bold uppercase transition-all ${!gameMode ? 'bg-white shadow-sm text-black' : 'text-gray-400 hover:text-gray-600'}`}
                        >
                            <Map className="w-3 h-3 mr-1" /> Map
                        </button>
                        <div className="w-px h-3 bg-gray-300 mx-1"></div>
                        <button 
                            onClick={() => setGameMode(true)}
                            className={`flex-1 flex items-center justify-center rounded text-[10px] font-bold uppercase transition-all ${gameMode ? 'bg-white shadow-sm text-black' : 'text-gray-400 hover:text-gray-600'}`}
                        >
                            <Gamepad2 className="w-3 h-3 mr-1" /> Game
                        </button>
                   </div>

                   <div className="w-12"></div> {/* Spacer for balance */}
                </div>                
                
                {/* ▼▼▼ [새로 추가하는 부분] 알림창 (Notification Popup) ▼▼▼ */}
                <div 
                    className={`absolute top-12 left-4 right-4 md:left-6 md:right-6 z-30 transition-all duration-500 ease-out will-change-transform transform 
                        ${showLog ? 'translate-y-0 opacity-100' : '-translate-y-4 opacity-0 pointer-events-none'}
                    `}
                >
                    <div className="bg-white/90 backdrop-blur-md rounded-[20px] p-4 shadow-[0_8px_30px_rgba(0,0,0,0.12)] border border-white/50 flex items-center gap-4 max-w-2xl mx-auto">
                        {/* 앱 아이콘 */}
                        <div className="w-10 h-10 rounded-[10px] bg-gradient-to-b from-white to-gray-50 flex items-center justify-center shadow-[0_1px_3px_rgba(0,0,0,0.1)] border border-black/5 flex-shrink-0">
                            <Map className="w-6 h-6 text-black" strokeWidth={1.5} />
                        </div>
                        
                        {/* 텍스트 내용 */}
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between mb-0.5">
                                <h3 className="text-[13px] font-bold text-black tracking-tight">RoutePick AI</h3>
                                <span className="text-[11px] text-gray-500 font-medium">실시간</span>
                            </div>
                            <p className="text-[13px] text-gray-900 font-medium leading-snug truncate pr-2">
                                {currentLog}
                            </p>
                        </div>
                    </div>
                </div>
                {/* ▲▲▲ [추가 완료] ▲▲▲ */}                
                
                {/* Screen Content */}
                <div className="absolute inset-0 pt-10 bg-gray-100 overflow-hidden">
                    {gameMode ? (
                        <TravelSnakeGame />
                    ) : (
                        <iframe 
                            src='https://my.spline.design/mapcopycopy-eHtXE3Yw41nPzqesI8XblKSL-AOA/' 
                            frameBorder='0' 
                            width='100%' 
                            height='100%'
                            className="w-full h-full origin-center"
                            title="Route Generation 3D"
                            style={{ border: 'none' }}
                        ></iframe>
                    )}
                </div>

                {/* Subtle Inner Shadow for Depth */}
                <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_40px_rgba(0,0,0,0.05)] rounded-[1.5rem] z-20"></div>
             </div>

             {/* 2. THE TABLET (iPad Landscape) */}
             {/* Replaced iPhone with iPad: aspect-[4/3], larger width, positioned to overlap bottom-right */}
             <div className={`absolute -bottom-20 -right-10 md:-bottom-48 md:-right-36 w-64 md:w-[58%] aspect-[4/3] bg-gray-900 rounded-[1.5rem] p-2 shadow-[0_20px_50px_rgba(0,0,0,0.5)] transform hover:rotate-0 transition-all duration-500 hidden md:block border border-gray-800
                ${gameMode 
                    ? 'z-0 opacity-40 scale-90 translate-y-10 rotate-[2deg]' 
                    : 'z-40 opacity-100 scale-100 rotate-[6deg]'
                }
             `}>
                <div className="w-full h-full bg-white rounded-[1.2rem] overflow-hidden relative border border-gray-100">
                    
                    {/* Screen Content - Sequential Animation */}
                    <div className="w-full h-full flex flex-col items-center justify-center p-6 bg-gray-50">
                        {/* Decorative Background Elements */}
                        <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none opacity-40">
                            <div className="absolute top-[-20%] left-[-20%] w-[80%] h-[50%] bg-blue-100 rounded-full blur-[40px] animate-pulse" />
                            <div className="absolute bottom-[-20%] right-[-20%] w-[80%] h-[50%] bg-indigo-50 rounded-full blur-[40px] animate-pulse delay-700" />
                        </div>

                        {/* Icon Container - Signigicantly Larger to fill removed text space. */}
                        <div className="relative w-32 h-32 md:w-40 md:h-40 mb-8 flex items-center justify-center">
                            {LOADING_STEPS.map((step, index) => {
                                const isActive = index === activeLoadingStep;
                                const gradientClass = STEP_COLORS[step.iconIndex % STEP_COLORS.length];
                                
                                return (
                                    <div
                                    key={index}
                                    className={`absolute top-0 left-0 w-full h-full flex items-center justify-center transition-all duration-700 ease-[cubic-bezier(0.4,0,0.2,1)]
                                        ${isActive 
                                        ? 'opacity-100 blur-0 scale-100 translate-y-0 z-10' 
                                        : 'opacity-0 blur-lg scale-90 translate-y-4 z-0'
                                        }
                                    `}
                                    >
                                    {/* COLOR GRADIENT APPLIED HERE - Larger Size */}
                                    <div 
                                        className={`w-24 h-24 md:w-32 md:h-32 bg-gradient-to-tr ${gradientClass} shadow-lg`}
                                        style={{
                                        maskImage: `url("${ICONS[step.iconIndex]}")`,
                                        WebkitMaskImage: `url("${ICONS[step.iconIndex]}")`,
                                        maskSize: 'contain',
                                        WebkitMaskSize: 'contain',
                                        maskRepeat: 'no-repeat',
                                        WebkitMaskRepeat: 'no-repeat',
                                        maskPosition: 'center',
                                        WebkitMaskPosition: 'center',
                                        }}
                                    />
                                    </div>
                                );
                            })}
                        </div>

                        {/* Text Container - Restored to Subtle Gray Style */}
                        <div className="h-12 w-full flex flex-col items-center justify-center relative text-center">
                            {LOADING_STEPS.map((step, index) => {
                            const isActive = index === activeLoadingStep;
                            return (
                                <div 
                                    key={index}
                                    className={`absolute inset-0 flex flex-col items-center justify-center transition-all duration-500 ease-[cubic-bezier(0.4,0,0.2,1)]
                                    ${isActive 
                                        ? 'opacity-100 translate-y-0 blur-0' 
                                        : 'opacity-0 translate-y-2 blur-sm'
                                    }
                                    `}
                                >
                                    {/* Removed Black Label, Only Small Gray Subtext Remaining */}
                                    <p className="text-sm text-gray-400 font-bold uppercase tracking-widest leading-tight">
                                        {step.subtext}
                                    </p>
                                </div>
                            );
                            })}
                        </div>

                        {/* Progress Dots */}
                        <div className="w-full mt-10 flex gap-1.5 justify-center">
                            {LOADING_STEPS.map((_, index) => (
                            <div 
                                key={index} 
                                className={`h-1.5 rounded-full transition-all duration-300
                                    ${index === activeLoadingStep ? 'w-4 bg-black' : 'w-1.5 bg-gray-300'}
                                `}
                            />
                            ))}
                        </div>
                    </div>

                    {/* Home Indicator (Longer for iPad) */}
                    <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-1/4 h-1 bg-gray-900 rounded-full opacity-20"></div>
                </div>
             </div>

        </div>

      </div>
    );
  }


  // --------------------------------------------------------------------------
  // COMPLETED
  // --------------------------------------------------------------------------
  if (isCompleted) {
    return (
      <div className="fixed inset-0 z-[60] bg-black text-white flex flex-col items-center justify-center text-center px-6">
        <h2 className="text-4xl md:text-6xl font-serif font-bold mb-6">여행 준비 완료.</h2>
        <p className="text-gray-400 mb-8 max-w-md">나만의 맞춤형 경로가 생성되었습니다. 이제 떠나볼까요?</p>
        <button onClick={onClose} className="px-8 py-3 bg-white text-black font-bold rounded-full hover:bg-gray-200 transition-colors">
            지도 보기
        </button>
      </div>
    );
  }

  // --------------------------------------------------------------------------
  // WIZARD FORM
  // --------------------------------------------------------------------------
  const stepData = steps[currentStep];

  return (
    <div className="fixed inset-0 z-[60] bg-white flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 md:px-12 py-6 border-b border-gray-100">
        <div className="text-sm font-bold tracking-widest uppercase text-gray-400">
          Step {currentStep + 1} / {steps.length}
        </div>
        <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
          <X className="w-6 h-6 text-black" />
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col justify-center px-6 md:px-12 max-w-4xl mx-auto w-full overflow-y-auto">
        <div className="mb-8 animate-fade-in-up">
            <span className="text-route-accent font-serif italic text-xl mb-2 block">{stepData.title}</span>
            <h2 className="text-3xl md:text-5xl font-bold text-black leading-tight word-keep-all">
            {stepData.question}
            </h2>
            
            {stepData.id === 'theme' && (
              <p className="mt-4 text-gray-400 text-sm md:text-base font-medium">
                Tip: 지역, 날씨, 여행 목적 등을 자세하게 입력하면 좋아요!
              </p>
            )}
        </div>

        <div className="min-h-[200px] animate-fade-in-up delay-100 pb-10">
            {/* STEP 1: THEME */}
            {stepData.id === 'theme' && (
                <div className="w-full">
                    <input 
                        type="text" 
                        autoFocus
                        placeholder="" 
                        value={formData.theme}
                        onChange={(e) => setFormData({...formData, theme: e.target.value})}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && formData.theme.trim()) {
                                handleNext();
                            }
                        }}
                        className="w-full text-2xl md:text-4xl border-b-2 border-gray-200 py-4 focus:border-black focus:outline-none bg-transparent transition-colors"
                    />
                    <div className="mt-6 text-gray-400 text-sm font-medium">
                        ex) 여자친구와 비 오는 날 강남 실내 데이트, 가족과의 잔잔한 전주 여행
                    </div>
                    <div className="mt-4 flex justify-start">
                        <button
                          type="button"
                          onClick={() => {
                            if (RANDOM_THEMES.length === 0) return;
                            let nextTheme = RANDOM_THEMES[Math.floor(Math.random() * RANDOM_THEMES.length)];
                            // 현재 테마와 동일하면 한 번 더 시도 (후보가 2개 이상일 때)
                            if (RANDOM_THEMES.length > 1 && nextTheme === formData.theme) {
                              nextTheme = RANDOM_THEMES[Math.floor(Math.random() * RANDOM_THEMES.length)];
                            }
                            setFormData(prev => ({ ...prev, theme: nextTheme }));
                          }}
                          className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-gray-200 text-sm font-medium text-gray-700 hover:border-black hover:text-black hover:bg-gray-50 transition-colors"
                        >
                          <Sparkles className="w-4 h-4" />
                          랜덤 테마 생성
                        </button>
                    </div>
                </div>
            )}

            {/* STEP 2: LOCATION */}
            {stepData.id === 'location' && (
                <div className="w-full">
                    <input 
                        type="text" 
                        autoFocus
                        placeholder="" 
                        value={formData.location}
                        onChange={(e) => setFormData({...formData, location: e.target.value})}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && formData.location.trim()) {
                                handleNext();
                            }
                        }}
                        className="w-full text-2xl md:text-4xl border-b-2 border-gray-200 py-4 focus:border-black focus:outline-none bg-transparent transition-colors"
                    />
                    <div className="mt-6 text-gray-400 text-sm font-medium">
                        ex) 서울 종로, 경기도 고양시
                    </div>
                </div>
            )}

            {/* STEP 3: GROUP SIZE */}
            {stepData.id === 'groupSize' && (
                <div className="space-y-6">
                    <div className="flex flex-wrap gap-4">
                        {['1명', '2명', '3명', '4명+'].map((num) => {
                            const isSelected = !isGroupSizeOther ? formData.groupSize === num : (num === '4명+' && isGroupSizeOther);
                            
                            return (
                                <button
                                    key={num}
                                    onClick={() => handleGroupSizeSelect(num)}
                                    className={`w-24 h-24 md:w-32 md:h-32 rounded-full text-lg md:text-xl font-bold border transition-all duration-300 flex items-center justify-center ${
                                        isSelected
                                        ? 'bg-black text-white border-black scale-110' 
                                        : 'bg-white text-black border-gray-200 hover:border-black'
                                    }`}
                                >
                                    {num}
                                </button>
                            );
                        })}
                    </div>
                    {isGroupSizeOther && (
                         <div className="animate-fade-in-up mt-6 w-full max-w-lg">
                            <label className="block text-xs text-gray-400 mb-2 font-bold uppercase tracking-widest">상세 인원 입력</label>
                            <input 
                                type="text"
                                autoFocus
                                placeholder="예: 6명"
                                value={formData.groupSize === '4명+' ? '' : formData.groupSize}
                                onChange={(e) => setFormData({...formData, groupSize: e.target.value})}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && formData.groupSize.trim()) {
                                        handleNext();
                                    }
                                }}
                                className="w-full text-xl md:text-2xl border-b-2 border-gray-200 py-3 focus:border-black focus:outline-none bg-transparent transition-colors"
                            />
                        </div>
                    )}
                </div>
            )}

            {/* STEP 4: DATE (Custom Calendar) */}
            {stepData.id === 'date' && (
                <div className="flex flex-col items-center">
                    {/* Date Display */}
                    <div className="flex w-full max-w-lg justify-between mb-8 gap-4">
                         <div className="w-1/2 p-4 border rounded-xl bg-gray-50 flex flex-col">
                            <span className="text-xs text-gray-400 font-bold uppercase mb-1">시작일</span>
                            <span className="text-lg font-bold">{formData.startDate || '-'}</span>
                         </div>
                         <div className="w-1/2 p-4 border rounded-xl bg-gray-50 flex flex-col">
                            <span className="text-xs text-gray-400 font-bold uppercase mb-1">종료일</span>
                            <span className="text-lg font-bold">{formData.endDate || '-'}</span>
                         </div>
                    </div>

                    {/* Calendar UI */}
                    <div className="w-full max-w-sm border border-gray-200 rounded-2xl p-6 bg-white shadow-sm">
                        <div className="flex items-center justify-between mb-6">
                            <button onClick={() => changeMonth(-1)} className="p-2 hover:bg-gray-100 rounded-full"><ChevronLeft className="w-5 h-5" /></button>
                            <span className="text-lg font-bold">
                                {currentMonth.getFullYear()}년 {String(currentMonth.getMonth() + 1).padStart(2, '0')}월
                            </span>
                            <button onClick={() => changeMonth(1)} className="p-2 hover:bg-gray-100 rounded-full"><ChevronRight className="w-5 h-5" /></button>
                        </div>
                        
                        <div className="grid grid-cols-7 gap-1 text-center mb-2">
                            {['일', '월', '화', '수', '목', '금', '토'].map(d => (
                                <div key={d} className="text-xs text-gray-400 font-bold py-2">{d}</div>
                            ))}
                        </div>
                        
                        <div className="grid grid-cols-7 gap-y-1 gap-x-0 justify-items-center">
                            {renderCalendar()}
                        </div>
                    </div>
                </div>
            )}

            {/* STEP 5: TIME */}
            {stepData.id === 'visitTime' && (
                <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                        {[
                            { label: '오전', time: '08:00 - 12:00' },
                            { label: '오후', time: '12:00 - 18:00' },
                            { label: '저녁', time: '18:00 - 24:00' },
                            { label: '하루종일', time: '00:00 - 24:00' },
                            { label: '기타', time: '직접 선택' },
                        ].map((item) => {
                            const isCustom = item.label === '기타';
                            const isSelected = isCustom ? isVisitTimeCustom : formData.visitTime === item.label;
                            
                            return (
                                <button
                                    key={item.label}
                                    onClick={() => {
                                        if (isCustom) {
                                            setIsVisitTimeCustom(true);
                                            setFormData({
                                                ...formData,
                                                visitTime: `기타(${String(customStartTime.hour).padStart(2, '0')}:${String(customStartTime.minute).padStart(2, '0')} - ${String(customEndTime.hour).padStart(2, '0')}:${String(customEndTime.minute).padStart(2, '0')})`,
                                            });
                                        } else {
                                            setIsVisitTimeCustom(false);
                                            setFormData({ ...formData, visitTime: item.label });
                                        }
                                    }}
                                    className={`py-6 px-6 rounded-xl border text-left transition-all duration-300 ${
                                        isSelected
                                        ? 'bg-black text-white border-black' 
                                        : 'bg-white text-black border-gray-200 hover:border-black'
                                    }`}
                                >
                                    <span className="block text-2xl font-bold mb-1">{item.label}</span>
                                    <span className={`text-xs ${isSelected ? 'opacity-80' : 'opacity-50'}`}>
                                        {isCustom && isVisitTimeCustom
                                            ? `${String(customStartTime.hour).padStart(2, '0')}:${String(customStartTime.minute).padStart(2, '0')} - ${String(customEndTime.hour).padStart(2, '0')}:${String(customEndTime.minute).padStart(2, '0')}`
                                            : item.time}
                                    </span>
                                </button>
                            );
                        })}
                    </div>

                    {isVisitTimeCustom && (
                        <div className="animate-fade-in-up mt-4 w-full max-w-xl">
                            <label className="block text-xs text-gray-400 mb-3 font-bold uppercase tracking-widest">
                                직접 방문 시간 설정
                            </label>
                            <div className="grid grid-cols-2 gap-6">
                                {/* 시작 시간 */}
                                <div>
                                    <span className="block text-sm text-gray-500 mb-2 font-medium">출발 시간</span>
                                    <div className="flex items-center gap-4">
                                        {/* Hour */}
                                        <div className="flex flex-col items-center">
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setCustomStartTime(prev => {
                                                        const nextHour = (prev.hour + 1) % 24;
                                                        const updated = { ...prev, hour: nextHour };
                                                        setFormData(f => ({
                                                            ...f,
                                                            visitTime: `기타(${String(updated.hour).padStart(2, '0')}:${String(updated.minute).padStart(2, '0')} - ${String(customEndTime.hour).padStart(2, '0')}:${String(customEndTime.minute).padStart(2, '0')})`,
                                                        }));
                                                        return updated;
                                                    });
                                                }}
                                                className="w-10 h-8 flex items-center justify-center rounded-md border border-gray-200 hover:bg-gray-100"
                                            >
                                                <ChevronLeft className="w-4 h-4 rotate-90" />
                                            </button>
                                            <div className="mt-1 mb-1 text-2xl font-semibold tabular-nums">
                                                {String(customStartTime.hour).padStart(2, '0')}
                                            </div>
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setCustomStartTime(prev => {
                                                        const nextHour = (prev.hour + 23) % 24;
                                                        const updated = { ...prev, hour: nextHour };
                                                        setFormData(f => ({
                                                            ...f,
                                                            visitTime: `기타(${String(updated.hour).padStart(2, '0')}:${String(updated.minute).padStart(2, '0')} - ${String(customEndTime.hour).padStart(2, '0')}:${String(customEndTime.minute).padStart(2, '0')})`,
                                                        }));
                                                        return updated;
                                                    });
                                                }}
                                                className="w-10 h-8 flex items-center justify-center rounded-md border border-gray-200 hover:bg-gray-100"
                                            >
                                                <ChevronLeft className="w-4 h-4 -rotate-90" />
                                            </button>
                                        </div>
                                        <span className="text-2xl font-semibold">:</span>
                                        {/* Minute */}
                                        <div className="flex flex-col items-center">
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setCustomStartTime(prev => {
                                                        const nextMinute = (prev.minute + 5) % 60;
                                                        const updated = { ...prev, minute: nextMinute };
                                                        setFormData(f => ({
                                                            ...f,
                                                            visitTime: `기타(${String(updated.hour).padStart(2, '0')}:${String(updated.minute).padStart(2, '0')} - ${String(customEndTime.hour).padStart(2, '0')}:${String(customEndTime.minute).padStart(2, '0')})`,
                                                        }));
                                                        return updated;
                                                    });
                                                }}
                                                className="w-10 h-8 flex items-center justify-center rounded-md border border-gray-200 hover:bg-gray-100"
                                            >
                                                <ChevronLeft className="w-4 h-4 rotate-90" />
                                            </button>
                                            <div className="mt-1 mb-1 text-2xl font-semibold tabular-nums">
                                                {String(customStartTime.minute).padStart(2, '0')}
                                            </div>
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setCustomStartTime(prev => {
                                                        const nextMinute = (prev.minute + 55) % 60; // -5분
                                                        const updated = { ...prev, minute: nextMinute };
                                                        setFormData(f => ({
                                                            ...f,
                                                            visitTime: `기타(${String(updated.hour).padStart(2, '0')}:${String(updated.minute).padStart(2, '0')} - ${String(customEndTime.hour).padStart(2, '0')}:${String(customEndTime.minute).padStart(2, '0')})`,
                                                        }));
                                                        return updated;
                                                    });
                                                }}
                                                className="w-10 h-8 flex items-center justify-center rounded-md border border-gray-200 hover:bg-gray-100"
                                            >
                                                <ChevronLeft className="w-4 h-4 -rotate-90" />
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                {/* 종료 시간 */}
                                <div>
                                    <span className="block text-sm text-gray-500 mb-2 font-medium">종료 시간</span>
                                    <div className="flex items-center gap-4">
                                        {/* Hour */}
                                        <div className="flex flex-col items-center">
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setCustomEndTime(prev => {
                                                        const nextHour = (prev.hour + 1) % 24;
                                                        const updated = { ...prev, hour: nextHour };
                                                        setFormData(f => ({
                                                            ...f,
                                                            visitTime: `기타(${String(customStartTime.hour).padStart(2, '0')}:${String(customStartTime.minute).padStart(2, '0')} - ${String(updated.hour).padStart(2, '0')}:${String(updated.minute).padStart(2, '0')})`,
                                                        }));
                                                        return updated;
                                                    });
                                                }}
                                                className="w-10 h-8 flex items-center justify-center rounded-md border border-gray-200 hover:bg-gray-100"
                                            >
                                                <ChevronLeft className="w-4 h-4 rotate-90" />
                                            </button>
                                            <div className="mt-1 mb-1 text-2xl font-semibold tabular-nums">
                                                {String(customEndTime.hour).padStart(2, '0')}
                                            </div>
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setCustomEndTime(prev => {
                                                        const nextHour = (prev.hour + 23) % 24;
                                                        const updated = { ...prev, hour: nextHour };
                                                        setFormData(f => ({
                                                            ...f,
                                                            visitTime: `기타(${String(customStartTime.hour).padStart(2, '0')}:${String(customStartTime.minute).padStart(2, '0')} - ${String(updated.hour).padStart(2, '0')}:${String(updated.minute).padStart(2, '0')})`,
                                                        }));
                                                        return updated;
                                                    });
                                                }}
                                                className="w-10 h-8 flex items-center justify-center rounded-md border border-gray-200 hover:bg-gray-100"
                                            >
                                                <ChevronLeft className="w-4 h-4 -rotate-90" />
                                            </button>
                                        </div>
                                        <span className="text-2xl font-semibold">:</span>
                                        {/* Minute */}
                                        <div className="flex flex-col items-center">
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setCustomEndTime(prev => {
                                                        const nextMinute = (prev.minute + 5) % 60;
                                                        const updated = { ...prev, minute: nextMinute };
                                                        setFormData(f => ({
                                                            ...f,
                                                            visitTime: `기타(${String(customStartTime.hour).padStart(2, '0')}:${String(customStartTime.minute).padStart(2, '0')} - ${String(updated.hour).padStart(2, '0')}:${String(updated.minute).padStart(2, '0')})`,
                                                        }));
                                                        return updated;
                                                    });
                                                }}
                                                className="w-10 h-8 flex items-center justify-center rounded-md border border-gray-200 hover:bg-gray-100"
                                            >
                                                <ChevronLeft className="w-4 h-4 rotate-90" />
                                            </button>
                                            <div className="mt-1 mb-1 text-2xl font-semibold tabular-nums">
                                                {String(customEndTime.minute).padStart(2, '0')}
                                            </div>
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setCustomEndTime(prev => {
                                                        const nextMinute = (prev.minute + 55) % 60; // -5분
                                                        const updated = { ...prev, minute: nextMinute };
                                                        setFormData(f => ({
                                                            ...f,
                                                            visitTime: `기타(${String(customStartTime.hour).padStart(2, '0')}:${String(customStartTime.minute).padStart(2, '0')} - ${String(updated.hour).padStart(2, '0')}:${String(updated.minute).padStart(2, '0')})`,
                                                        }));
                                                        return updated;
                                                    });
                                                }}
                                                className="w-10 h-8 flex items-center justify-center rounded-md border border-gray-200 hover:bg-gray-100"
                                            >
                                                <ChevronLeft className="w-4 h-4 -rotate-90" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* STEP 6: TRANSPORTATION */}
            {stepData.id === 'transportation' && (
                <div className="space-y-6">
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                        {[
                            { id: 'Walk', label: '도보', icon: Footprints },
                            { id: 'Subway', label: '지하철', icon: Train },
                            { id: 'Bus', label: '버스', icon: Bus },
                            { id: 'Car', label: '자동차', icon: Car },
                            { id: 'Other', label: '기타', icon: MoreHorizontal },
                        ].map((mode) => {
                            const isSelected = mode.label === '기타' 
                                ? isTransportOther 
                                : formData.transportation.includes(mode.label);

                            return (
                                <button
                                    key={mode.id}
                                    onClick={() => toggleTransport(mode.label)}
                                    className={`aspect-square rounded-xl border flex flex-col items-center justify-center gap-4 transition-all duration-300 ${
                                        isSelected
                                        ? 'bg-black text-white border-black' 
                                        : 'bg-white text-black border-gray-200 hover:border-black'
                                    }`}
                                >
                                    <mode.icon className="w-8 h-8" />
                                    <span className="font-medium text-lg">{mode.label}</span>
                                </button>
                            )
                        })}
                    </div>
                    {isTransportOther && (
                        <div className="animate-fade-in-up mt-6 w-full">
                            <label className="block text-xs text-gray-400 mb-2 font-bold uppercase tracking-widest">기타 이동 수단 입력</label>
                            <input 
                                type="text" 
                                autoFocus
                                placeholder="예: 자전거, 킥보드"
                                value={formData.customTransport}
                                onChange={(e) => setFormData({...formData, customTransport: e.target.value})}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && formData.customTransport.trim()) {
                                        handleNext();
                                    }
                                }}
                                className="w-full text-xl md:text-2xl border-b-2 border-gray-200 py-3 focus:border-black focus:outline-none bg-transparent transition-colors"
                            />
                        </div>
                    )}
                </div>
            )}

            {/* STEP 7: BUDGET */}
            {stepData.id === 'budget' && (
                <div className="w-full">
                    <p className="mb-6 text-gray-500 text-sm font-medium">
                        예산을 입력하시면 예산에 맞는 코스를 추천해드립니다. (선택사항)
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                        {[
                            { label: '5만원 이하', value: '50000' },
                            { label: '5만원~10만원', value: '100000' },
                            { label: '10만원~20만원', value: '200000' },
                            { label: '20만원~50만원', value: '500000' },
                            { label: '50만원 이상', value: '1000000' },
                            { label: '직접 입력', value: 'custom' },
                        ].map((option) => {
                            const isSelected = formData.budget === option.value || 
                                (option.value === 'custom' && formData.budget && !['50000', '100000', '200000', '500000', '1000000'].includes(formData.budget));
                            
                            return (
                                <button
                                    key={option.value}
                                    onClick={() => {
                                        if (option.value === 'custom') {
                                            setFormData({...formData, budget: ''});
                                        } else {
                                            setFormData({...formData, budget: option.value});
                                        }
                                    }}
                                    className={`py-6 px-6 rounded-xl border text-left transition-all duration-300 ${
                                        isSelected
                                        ? 'bg-black text-white border-black' 
                                        : 'bg-white text-black border-gray-200 hover:border-black'
                                    }`}
                                >
                                    <span className="block text-xl font-bold">{option.label}</span>
                                </button>
                            );
                        })}
                    </div>
                    {(formData.budget === '' || !['50000', '100000', '200000', '500000', '1000000'].includes(formData.budget)) && (
                        <div className="animate-fade-in-up mt-6 w-full">
                            <label className="block text-xs text-gray-400 mb-2 font-bold uppercase tracking-widest">예산 직접 입력 (원)</label>
                            <input 
                                type="text" 
                                autoFocus
                                placeholder="예: 150000 (선택사항)"
                                value={formData.budget}
                                onChange={(e) => {
                                    const value = e.target.value.replace(/[^0-9]/g, '');
                                    setFormData({...formData, budget: value});
                                }}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                        handleNext();
                                    }
                                }}
                                className="w-full text-2xl md:text-4xl border-b-2 border-gray-200 py-4 focus:border-black focus:outline-none bg-transparent transition-colors"
                            />
                            <div className="mt-6 text-gray-400 text-sm font-medium">
                                ex) 150000 (15만원), 500000 (50만원) - 입력하지 않아도 됩니다
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* STEP 8: REVIEW */}
            {stepData.id === 'review' && (
                <div className="bg-gray-50 p-8 rounded-2xl border border-gray-100">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-y-8 gap-x-12">
                        <div>
                            <span className="text-xs text-gray-400 uppercase tracking-widest block mb-1">여행 테마 (Theme)</span>
                            <p className="text-xl font-medium break-keep">{formData.theme || '입력되지 않음'}</p>
                        </div>
                        <div>
                            <span className="text-xs text-gray-400 uppercase tracking-widest block mb-1">지역 (Location)</span>
                            <p className="text-xl font-medium break-keep">{formData.location || '입력되지 않음'}</p>
                        </div>
                        <div>
                            <span className="text-xs text-gray-400 uppercase tracking-widest block mb-1">여행 인원 (Travelers)</span>
                            <p className="text-xl font-medium">{formData.groupSize || '입력되지 않음'}</p>
                        </div>
                         <div>
                            <span className="text-xs text-gray-400 uppercase tracking-widest block mb-1">일정 (Schedule)</span>
                            <p className="text-xl font-medium">
                                {formData.startDate} {formData.endDate ? `~ ${formData.endDate}` : ''}
                                <span className="text-gray-400 text-base ml-2">({formData.visitTime})</span>
                            </p>
                        </div>
                         <div className="md:col-span-2">
                            <span className="text-xs text-gray-400 uppercase tracking-widest block mb-1">이동 수단 (Transport)</span>
                            <div className="flex gap-2 mt-1 flex-wrap">
                                {formData.transportation.map(t => (
                                    <span key={t} className="px-4 py-1.5 bg-white border border-gray-200 rounded-full text-sm font-medium">{t}</span>
                                ))}
                                {isTransportOther && formData.customTransport && (
                                     <span className="px-4 py-1.5 bg-white border border-gray-200 rounded-full text-sm font-medium">{formData.customTransport}</span>
                                )}
                                {formData.transportation.length === 0 && (!isTransportOther || !formData.customTransport) && (
                                    <span className="text-gray-400 italic">선택안함</span>
                                )}
                            </div>
                        </div>
                        <div>
                            <span className="text-xs text-gray-400 uppercase tracking-widest block mb-1">예산 (Budget)</span>
                            <p className="text-xl font-medium">
                                {formData.budget ? `${parseInt(formData.budget).toLocaleString()}원` : '입력되지 않음'}
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
      </div>

      {/* Footer / Navigation */}
      <div className="px-6 md:px-12 py-8 border-t border-gray-100 flex justify-between items-center bg-white/80 backdrop-blur-sm">
        <button 
            onClick={handleBack} 
            disabled={currentStep === 0}
            className={`flex items-center gap-2 text-sm font-bold uppercase tracking-widest transition-opacity hover:opacity-100 ${currentStep === 0 ? 'opacity-0 pointer-events-none' : 'opacity-40'}`}
        >
            <ArrowLeft className="w-4 h-4" /> 이전 (Back)
        </button>

        <button 
            onClick={handleNext}
            className="group flex items-center gap-3 bg-black text-white px-8 py-4 rounded-full font-bold uppercase tracking-widest text-sm hover:bg-gray-800 transition-all shadow-lg hover:shadow-xl"
        >
            {currentStep === steps.length - 1 ? '여행 생성하기' : '다음 단계'}
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    </div>
  );
};

export default TripPlanner;