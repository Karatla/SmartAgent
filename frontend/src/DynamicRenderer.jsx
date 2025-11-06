import ProductTable from "./components/ProductTable";
import SalesChart from "./components/SalesChart";

const resolveData = (datasets, source) => {
  if (!datasets) return [];
  if (source && datasets[source]) return datasets[source];
  if (datasets.data) return datasets.data;
  const firstKey = Object.keys(datasets)[0];
  return firstKey ? datasets[firstKey] : [];
};

export default function DynamicRenderer({ layout, datasets }) {
  if (!layout) return null;

  switch (layout.type) {
    case "Page":
      return (
        <div>
          {layout.title ? (
            <h2 className="text-xl font-semibold mb-2">{layout.title}</h2>
          ) : null}
          {layout.children?.map((child, i) => (
            <DynamicRenderer key={i} layout={child} datasets={datasets} />
          ))}
        </div>
      );

    case "Table":
      return <ProductTable data={resolveData(datasets, layout.source)} />;

    case "Chart":
      return (
        <SalesChart
          data={resolveData(datasets, layout.source)}
          chartType={layout.chartType}
          metric={layout.metric}
        />
      );

    case "Text":
      return <p>{layout.content}</p>;

    default:
      return <p>Unknown layout type: {layout.type}</p>;
  }
}
