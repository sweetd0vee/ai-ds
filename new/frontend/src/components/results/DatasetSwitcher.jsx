export default function DatasetSwitcher({ items, value, onChange }) {
  if (!items?.length || items.length < 2) return null

  return (
    <div className="dataset-tabs" role="tablist" aria-label="Таблицы">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={value === item.id}
          className={`dataset-tab ${value === item.id ? 'active' : ''}`}
          onClick={() => onChange(item.id)}
          title={item.name}
        >
          <span className="dataset-tab-name">{item.label || item.name}</span>
          {(item.rows != null && item.cols != null) && (
            <span className="dataset-tab-meta">{item.rows} × {item.cols}</span>
          )}
        </button>
      ))}
    </div>
  )
}
