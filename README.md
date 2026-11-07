# קליבר: האפליקציה

הקוד של האפליקציה של קליבר, סוכן מחקר הסווינג של ליעד. הוא מוגש ב-GitHub Pages מהריפו הציבורי הזה.
**אין כאן שום נתון.** כל הנתונים נמצאים בריפו הפרטי `2000liad/caliber-relay`, והדף קורא וכותב אותם דרך ה-REST API של גיטהאב,
עם טוקן fine-grained שהבעלים מדביק פעם אחת בכל דפדפן. הטוקן נשמר ב-localStorage של הדפדפן, ונשלח רק ל-`api.github.com`.

## מה יש כאן
- `index.html`: האפליקציה כולה (HTML, CSS ו-JS בקובץ אחד). המסכים הם אלה של האפליקציה ב-claude.ai (גרסה מ-4.11.2026).
  הם הועברו כמעט כמו שהם, ושכבת הנתונים שלהם (`GHDB`) מדברת עכשיו עם גיטהאב במקום עם ה-db של claude.ai.
- `dev/mockgh.py`: שרת מקומי שמחקה את החלק של ה-API שהדף צריך, לבדיקות בלי טוקן אמיתי:
  `python3 dev/mockgh.py <תיקייה בצורת caliber-relay> 8766`, ואז http://localhost:8766 עם הטוקן `test-token`.

## איפה הנתונים, בריפו הפרטי
| נתיב | מי כותב | מה |
|---|---|---|
| `app/data/<collection>.json` | המנוע בענן | `{id: doc}` לכל אוסף: calls, events, stats, screen, meta, live, positions, engine, queue, qa |
| `app/data/reports/<id>.json`, `app/data/outcomes/<id>.json` | המנוע בענן | מסמך לכל קריאה, נטען כשפותחים אותה |
| `app/user/journal.json`, `app/user/settings.json` | הדף | יומן המסחר וגודל התיק |
| issues עם התווית `caliber-request` | הדף | בקשות ושאלות. פתיחה של issue מעירה את המנוע |
| `relay/state/worker-lock.json` | המנוע בענן | קיים רק בזמן שהמנוע עובד |

הפירוט המלא של הזרימה נמצא ב-`HANDOFF.md` וב-`relay/WORKER.md` בריפו הפרטי.
