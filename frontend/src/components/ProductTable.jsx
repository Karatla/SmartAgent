export default function ProductTable({ data }) {
  return (
    <table className="border border-gray-300 w-full">
      <thead>
        <tr>
          <th className="border p-2">ID</th>
          <th className="border p-2">Name</th>
          <th className="border p-2">Price ($)</th>
        </tr>
      </thead>
      <tbody>
        {data?.map((p) => (
          <tr key={p.id}>
            <td className="border p-2">{p.id}</td>
            <td className="border p-2">{p.name}</td>
            <td className="border p-2">{p.price}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
