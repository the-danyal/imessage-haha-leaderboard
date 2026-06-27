# iMessage Haha Leaderboard

See who makes your group chat laugh the most and who never does.

Reads your iMessage history directly from your Mac and generates a leaderboard of Haha reactions for any group chat.

## Example output

```
==============================================================
                     HAHA LEADERBOARD
                    Since August 04, 2024
==============================================================

  Jordan
    Hahas Given:             342
    Hahas Received:          891
    Messages Sent:         1,204
    Hahas Received/Msg:    0.740
    Hahas Given/Msg:       0.284

    Most laughed message (14 hahas):
    > "bro i just walked into the wrong class and sat down for 10 minutes"
    Context:
      Alex: where are you
      Sam: he's not here yet
      Jordan: bro i just walked into the wrong class and sat down for 10 minutes

  Alex
    Hahas Given:             614
    Hahas Received:          503
    Messages Sent:         2,847
    Hahas Received/Msg:    0.177
    Hahas Given/Msg:       0.216

    Most laughed message (9 hahas):
    > "i set 7 alarms and slept through all of them"

==============================================================
              TOP 10 MOST LAUGHED MESSAGES
==============================================================

  #1 (14 hahas) — Jordan
  "bro i just walked into the wrong class and sat down for 10 minutes"

  #2 (11 hahas) — Sam
  "my mom just texted me 'call me' with a period. i am not okay"

  #3 (9 hahas) — Alex
  "i set 7 alarms and slept through all of them"

==============================================================
         AWARDS  (based on hahas per message sent)
==============================================================

  Jester        — Jordan (0.740 hahas received/msg)
  Brick         — Mike (0.031 hahas received/msg)
  Chucklenuts   — Alex (0.216 hahas given/msg)
  Debbie Downer — Sam (0.044 hahas given/msg)
```

## What it shows

**Per person:**
- Hahas given / received
- Messages sent
- Hahas received per message sent
- Hahas given per message sent
- Their most laughed-at message (with context)

**Group:**
- Top 10 most laughed-at messages of all time

**Awards** *(based on hahas per message sent)*
- **Jester** — most hahas received per message
- **Brick** — least hahas received per message
- **Chucklenuts** — most hahas given per message
- **Debbie Downer** — least hahas given per message

## Requirements

- Mac with iMessage
- Python 3 (pre-installed on macOS)
- No third-party packages needed

## Setup

**1. Grant Terminal full disk access**

`System Settings → Privacy & Security → Full Disk Access → enable Terminal`

**2. Configure your group members**

```bash
cp names_example.json names.json
```

Edit `names.json` with your group's phone numbers and names:

```json
{
  "MY_NAME": "Alex",
  "+14155550101": "Jordan",
  "+14155550102": "Sam"
}
```

- `MY_NAME` is your own name (for messages you sent)
- Keys are phone numbers in `+countrycode` format works for any country
- Only people listed here are included in the report; everyone else is ignored

**3. Run it**

```bash
python3 haha_leaderboard.py
```

You'll be shown a list of your group chats and asked to pick one. You can merge multiple chats (e.g. if your group was renamed) by entering numbers separated by commas: `1,2`

## Privacy

`names.json` is gitignored, your contacts never leave your machine. The script reads `chat.db` locally and prints to your terminal. Nothing is uploaded anywhere.

## Finding phone numbers

Not sure what number to put? Open Messages, tap on a contact in the group, and check their info. The number needs to match exactly how iMessage stores it (`+1XXXXXXXXXX` for US, `+44XXXXXXXXXX` for UK, etc.).
