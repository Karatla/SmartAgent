import { BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

export default function SalesChart({ data }) {
  if (!Array.isArray(data) || data.length === 0) {
    return <p className="text-sm text-gray-500">No sales data available.</p>;
  }

  return (
    <div className="flex w-full items-center justify-center py-2">
      <BarChart width={500} height={300} data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="total" fill="#4f46e5" />
      </BarChart>
    </div>
  );
}
