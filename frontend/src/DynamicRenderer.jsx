import ProductTable from "./components/ProductTable";
import SalesChart from "./components/SalesChart";

export default function DynamicRenderer({ layout, data }) {
  if (!layout) return null;

  switch (layout.type) {
    case "Page":
      return (
        <div>
          <h2 className="text-xl font-semibold mb-2">{layout.title}</h2>
          {layout.children?.map((child, i) => (
            <DynamicRenderer key={i} layout={child} data={data} />
          ))}
        </div>
      );

    case "Table":
      return <ProductTable data={data} />;

    case "Chart":
      return <SalesChart data={data} chartType={layout.chartType} />;

    case "Text":
      return <p>{layout.content}</p>;

    default:
      return <p>Unknown layout type</p>;
  }
}
