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

const STATUS_STYLES = {
  Active:    "bg-emerald-950 text-emerald-400 ring-1 ring-emerald-800",
  Dormant:   "bg-yellow-950 text-yellow-400 ring-1 ring-yellow-800",
  Converted: "bg-blue-950 text-blue-400 ring-1 ring-blue-800",
  Dead:      "bg-gray-800 text-gray-500 ring-1 ring-gray-700",
};

function SectionLabel({ children }) {
  return (
    <p className="text-xs font-semibold tracking-widest uppercase text-gray-500 mb-3">
      {children}
    </p>
  );
}

export default async function Page() {
  const [contacts, followups] = await Promise.all([getContacts(), getFollowups()]);
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="space-y-10">

      {/* Follow-ups */}
      <section>
        <div className="flex items-end justify-between mb-3">
          <SectionLabel>Follow-ups due</SectionLabel>
          <span className="text-xs text-gray-600 mb-3">next 7 days · {followups.length} contact{followups.length !== 1 ? "s" : ""}</span>
        </div>

        {followups.length === 0 ? (
          <div className="rounded-lg border border-gray-800 bg-gray-900 px-6 py-8 text-center text-sm text-gray-600">
            No follow-ups due in the next 7 days.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {followups.map((f) => (
              <div
                key={f.id}
                className={`rounded-lg border bg-gray-900 px-5 py-4 flex flex-col gap-1 ${
                  f.overdue
                    ? "border-l-2 border-l-red-500 border-t-gray-800 border-r-gray-800 border-b-gray-800"
                    : "border-gray-800"
                }`}
              >
                <span className="font-semibold text-sm text-white">{f.name}</span>
                <span className="text-xs text-gray-500">{f.company}</span>
                <span className={`text-xs font-medium mt-2 ${f.overdue ? "text-red-400" : "text-blue-400"}`}>
                  {f.overdue ? "Overdue" : "Due"} &mdash; {f.nextFollowup}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Contacts table */}
      <section>
        <div className="flex items-end justify-between mb-3">
          <SectionLabel>All contacts</SectionLabel>
          <span className="text-xs text-gray-600 mb-3">{contacts.length} total</span>
        </div>

        <div className="rounded-lg border border-gray-800 overflow-hidden">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-900">
                {["Name", "Company", "Status", "Tags", "Last Contact", "Next Follow-up"].map((h) => (
                  <th key={h} className="px-5 py-3 text-left text-xs font-semibold tracking-widest uppercase text-gray-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-gray-950 divide-y divide-gray-800">
              {contacts.map((c) => {
                const overdue = c.nextFollowup && c.nextFollowup < today;
                return (
                  <tr key={c.id} className="hover:bg-gray-900 transition-colors">
                    <td className="px-5 py-3.5 font-medium text-white">{c.name}</td>
                    <td className="px-5 py-3.5 text-gray-400">{c.company}</td>
                    <td className="px-5 py-3.5">
                      {c.status && (
                        <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[c.status] ?? "bg-gray-800 text-gray-400"}`}>
                          {c.status}
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-gray-500 text-xs">{c.tags}</td>
                    <td className="px-5 py-3.5 text-gray-500 tabular-nums">{c.lastContact}</td>
                    <td className={`px-5 py-3.5 tabular-nums text-xs font-medium ${overdue ? "text-red-400" : "text-gray-500"}`}>
                      {c.nextFollowup}
                    </td>
                  </tr>
                );
              })}
              {contacts.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-10 text-center text-gray-600">
                    No contacts found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

    </div>
  );
}
