import { Client } from "@notionhq/client";

const CONTACTS_DB_ID = "d87f84dc2ca046109a9eb0ce371ff690";

function extract(prop) {
  if (!prop) return "";
  switch (prop.type) {
    case "title":        return prop.title.map((r) => r.plain_text).join("");
    case "rich_text":    return prop.rich_text.map((r) => r.plain_text).join("");
    case "email":        return prop.email ?? "";
    case "select":       return prop.select?.name ?? "";
    case "multi_select": return prop.multi_select.map((o) => o.name).join(", ");
    case "date":         return prop.date?.start ?? "";
    default:             return "";
  }
}

function getNotion() {
  return new Client({ auth: process.env.NOTION_API_KEY });
}

async function getContacts() {
  const notion = getNotion();
  const pages = [];
  let cursor;

  do {
    const res = await notion.databases.query({
      database_id: CONTACTS_DB_ID,
      sorts: [{ property: "Name", direction: "ascending" }],
      ...(cursor ? { start_cursor: cursor } : {}),
    });
    pages.push(...res.results);
    cursor = res.has_more ? res.next_cursor : null;
  } while (cursor);

  return pages.map((p) => ({
    id: p.id,
    name:         extract(p.properties["Name"]),
    company:      extract(p.properties["Company"]),
    status:       extract(p.properties["Status"]),
    tags:         extract(p.properties["Tags"]),
    lastContact:  extract(p.properties["Last Contact"]),
    nextFollowup: extract(p.properties["Next Follow-up"]),
  }));
}

async function getFollowups() {
  const notion = getNotion();
  const today = new Date().toISOString().slice(0, 10);
  const inSevenDays = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);

  const res = await notion.databases.query({
    database_id: CONTACTS_DB_ID,
    filter: {
      and: [
        { property: "Next Follow-up", date: { is_not_empty: true } },
        { property: "Next Follow-up", date: { on_or_before: inSevenDays } },
        { property: "Status", select: { does_not_equal: "Dead" } },
      ],
    },
    sorts: [{ property: "Next Follow-up", direction: "ascending" }],
  });

  return res.results.map((p) => ({
    id: p.id,
    name:         extract(p.properties["Name"]),
    company:      extract(p.properties["Company"]),
    nextFollowup: extract(p.properties["Next Follow-up"]),
    overdue:      extract(p.properties["Next Follow-up"]) < today,
  }));
}

const STATUS_COLORS = {
  Active:    "bg-green-100 text-green-800",
  Dormant:   "bg-yellow-100 text-yellow-800",
  Converted: "bg-blue-100 text-blue-800",
  Dead:      "bg-gray-100 text-gray-500",
};

export default async function Page() {
  const [contacts, followups] = await Promise.all([getContacts(), getFollowups()]);

  return (
    <div className="space-y-8">

      {/* Follow-ups panel */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xl font-semibold">Follow-ups due</h2>
          <span className="text-sm text-gray-500">next 7 days</span>
        </div>

        {followups.length === 0 ? (
          <p className="text-sm text-gray-400 bg-white border border-gray-200 rounded-lg px-4 py-6 text-center">
            Nothing due in the next 7 days.
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {followups.map((f) => (
              <div
                key={f.id}
                className={`rounded-lg border px-4 py-3 bg-white ${
                  f.overdue ? "border-red-300 bg-red-50" : "border-gray-200"
                }`}
              >
                <div className="font-medium text-sm">{f.name}</div>
                <div className="text-xs text-gray-500 mt-0.5">{f.company}</div>
                <div className={`text-xs mt-2 font-medium ${f.overdue ? "text-red-600" : "text-gray-600"}`}>
                  {f.overdue ? "Overdue · " : "Due · "}{f.nextFollowup}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Contacts table */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xl font-semibold">Contacts</h2>
          <span className="text-sm text-gray-500">{contacts.length} total</span>
        </div>

        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Company</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Tags</th>
                <th className="px-4 py-3">Last Contact</th>
                <th className="px-4 py-3">Next Follow-up</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {contacts.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{c.name}</td>
                  <td className="px-4 py-3 text-gray-600">{c.company}</td>
                  <td className="px-4 py-3">
                    {c.status && (
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[c.status] ?? "bg-gray-100 text-gray-600"}`}>
                        {c.status}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{c.tags}</td>
                  <td className="px-4 py-3 text-gray-600">{c.lastContact}</td>
                  <td className="px-4 py-3 text-gray-600">{c.nextFollowup}</td>
                </tr>
              ))}
              {contacts.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                    No contacts found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
