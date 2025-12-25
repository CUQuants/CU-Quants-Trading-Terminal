import { ReactNode } from 'react'
import styles from './DataTable.module.css'

export interface Column<T> {
  key: keyof T | string
  header: string
  align?: 'left' | 'right' | 'center'
  render?: (value: any, row: T) => ReactNode
  className?: string
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  keyField: keyof T
  onRowClick?: (row: T) => void
  className?: string
}

function DataTable<T>({ columns, data, keyField, onRowClick, className }: DataTableProps<T>) {
  const getCellValue = (row: T, column: Column<T>) => {
    if (column.render) {
      return column.render(row[column.key as keyof T], row)
    }
    return String(row[column.key as keyof T] || '')
  }

  return (
    <div className={`${styles.tableContainer} ${className || ''}`}>
      <table className={styles.table}>
        <thead>
          <tr>
            {columns.map((column, index) => (
              <th 
                key={`header-${index}`}
                className={`${styles[`align-${column.align || 'left'}`]} ${column.className || ''}`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className={styles.emptyState}>
                No data available
              </td>
            </tr>
          ) : (
            data.map((row) => (
              <tr 
                key={String(row[keyField])}
                onClick={() => onRowClick?.(row)}
                className={onRowClick ? styles.clickable : ''}
              >
                {columns.map((column, index) => (
                  <td 
                    key={`cell-${index}`}
                    className={`${styles[`align-${column.align || 'left'}`]} ${column.className || ''}`}
                  >
                    {getCellValue(row, column)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}

export default DataTable
