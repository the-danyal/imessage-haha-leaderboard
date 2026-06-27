# iMessage Haha Leaderboard

See who makes your group chat laugh the most and who never does.

Reads your iMessage history directly from your Mac and generates a leaderboard of Haha reactions for any group chat.

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
