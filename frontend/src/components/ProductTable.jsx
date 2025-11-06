const fallbackKey = (row, index) => {
  if (row?.id != null) return row.id;
  if (row?.sku != null) return row.sku;
  if (row?.key != null) return row.key;
  return `row-${index}`;
};

const formatHeader = (key) =>
  key
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, (c) => c.toUpperCase());

export default function ProductTable({ data }) {
  const rows = Array.isArray(data) ? data : [];
  if (!rows.length) {
    return <p className="text-sm text-gray-500">No records found.</p>;
  }

  const columns = Object.keys(rows[0]);

  return (
    <table className="border border-gray-300 w-full text-sm">
      <thead>
        <tr>
          {columns.map((col) => (
            <th key={col} className="border p-2 text-left">
              {formatHeader(col)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, rowIndex) => (
          <tr key={fallbackKey(row, rowIndex)}>
            {columns.map((col) => (
              <td key={col} className="border p-2">
                {row[col] != null ? String(row[col]) : "—"}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
