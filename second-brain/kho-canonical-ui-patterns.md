# kho (warehouse) — Canonical UI Patterns for List Pages, Grids, Filters, Overviews & Spacing

**Mục đích**: Đây là nguồn sự thật duy nhất (single source of truth) về cách module kho được implement đúng và nhất quán. Tất cả màn hình list, table, filter, overview sau này PHẢI copy theo đúng pattern này để tránh lặp lại lỗi:
- "Expected corresponding JSX closing tag for <Container>"
- "JSX elements cannot have multiple attributes with the same name" (duplicate tableLayout / tableClassNames / enableHorizontalScroll / pinnedRightColumns sau khi edit)
- Gap thừa giữa header/filter và table, search có label sai, missing pinned actions, header không sticky, scroll ngang hỏng, mt-2 thừa, nesting sai, KpiCard style lệch, v.v.

**Nguyên tắc**: 
- Kho là "Loại A" (advanced filter + sidebar + my-filters). Đây là pattern reference sau các lần fix cho bed, inpatient, schedule, hospital-management.
- Chỉ khi trang thật sự đơn giản (không có advanced filter + sidebar) thì mới dùng biến thể có title Toolbar.
- Overview/dashboard có quy tắc padding + KpiCard riêng.
- **Không bao giờ** tự sáng tạo spacing/layout. Copy nguyên khối từ kho trước.

---

## 1. Quyết định loại trang (Decision Tree)

| Loại | Khi nào dùng | Có title Toolbar? | Có advanced filter + sidebar? | Cấu trúc chính |
|------|--------------|-------------------|-------------------------------|----------------|
| **Loại A (kho chuẩn)** | List có filter nâng cao, my-filters, sidebar (Inventory, StockTake, ProductPrice, ...) | ❌ Không | ✅ Có (`filterSidebarVisible`, `InventoryFilterSidebar` v.v.) | Container > flex-1 > gap-3 (khi visible) > div pe-1 pt-3.5 > EnhancedDataGrid + Sidebar sibling |
| **Loại B (titled đơn giản)** | Danh mục nhỏ, không cần sidebar phức tạp (DisposalReason, ManualAdjustmentReason, một số master) | ✅ Có (Toolbar + ToolbarHeading + ToolbarPageTitle) | ❌ Thường không | Container > flex-col gap-2 > flex-shrink-0 Toolbar > grid area |
| **Overview / Dashboard** | Tổng quan kho | N/A (Tabs header riêng) | N/A | Container > header `px-3 pt-2` > content `px-4 py-4 space-y-4` + KpiCard grid |

**Quy tắc**: 
- Advanced list (có my-filters + SlidersHorizontal button + sidebar) → luôn Loại A, **không** để Toolbar title.
- Nếu copy từ disposal-reason mà bỏ title → phải xóa đúng số lượng div wrapper (tránh thừa `</div>` gây lỗi Container tag).

---

## 2. Cấu trúc Loại A (Canonical — inventory-list-page.tsx)

### Outer wrapper (quan trọng nhất — copy y nguyên)

```tsx
<Container className="h-full flex flex-col overflow-hidden">
  <div className="flex flex-1 flex-col min-h-0 overflow-hidden">
    <div className={`flex flex-1 min-h-0 overflow-hidden ${filterSidebarVisible ? "gap-3" : ""}`}>
      <div className="flex flex-1 flex-col min-h-0 overflow-hidden pe-1 pt-3.5">
        <EnhancedDataGrid
          ...
        />
      </div>

      <YourFilterSidebar visible={filterSidebarVisible} filter={...} onApply={...} />
    </div>
  </div>

  {/* Dialogs + FormSheets ở cuối, cùng cấp với 2 div trên */}
</Container>
```

**Quy tắc nghiêm ngặt**:
- `pe-1 pt-3.5` trên div bao EnhancedDataGrid (để tạo padding phải/trên khi không có title).
- `gap-3` **chỉ** khi `filterSidebarVisible === true`.
- Không có `<div className="flex-shrink-0">` + Toolbar title ở đầu.
- `min-h-0` và `overflow-hidden` ở đúng cấp để scroll + flex hoạt động.

### State filter sidebar

```tsx
const [filterSidebarVisible, setFilterSidebarVisible] = useState(false)
```

Mặc định **false**.

---

## 3. Search + My-Filters + Actions trong toolbar của EnhancedDataGrid (Loại A)

Bên trong `toolbar={<>` :

```tsx
<>
  {/* Search — KHÔNG dùng <label> */}
  <div className="relative w-[250px] flex-shrink-0">
    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
    <Input
      value={searchQuery}
      onChange={(e) => setSearchQuery(e.target.value)}
      placeholder="Tên kho, mã kho"
      className="ps-9"
    />
  </div>

  <div className="flex items-center gap-2 ms-auto">
    {/* My Filters Dropdown — chuẩn */}
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="md" className="w-[160px] justify-between">
          <span className="flex items-center gap-2 truncate">
            <Bookmark className="size-4 shrink-0" />
            <span className="truncate">{selectedFilterName || 'Bộ lọc của tôi'}</span>
          </span>
          <ChevronDown className="size-4 shrink-0" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[250px]">
        {selectedFilterName && (
          <DropdownMenuItem onSelect={() => { setAdvancedFilter(empty...); setSelectedFilterName(''); }}>
            Bỏ chọn bộ lọc
          </DropdownMenuItem>
        )}
        {myFilters.length === 0 && !selectedFilterName ? (
          <div className="px-3 py-4 text-sm text-muted-foreground text-center">Chưa có bộ lọc nào</div>
        ) : (
          myFilters.map(f => (
            <DropdownMenuItem key={f.Id} ... onSelect={load filter}>
              <span className="truncate flex-1">{f.FilterName}</span>
              <div className="flex items-center gap-0.5 shrink-0">
                <button onClick={e => {e.stopPropagation(); setDefault...}}>
                  <Star className={f.IsDefault ? 'text-yellow-500 fill-yellow-500' : ''} />
                </button>
                <button onClick={e => {e.stopPropagation(); delete...}}>
                  <Trash2 />
                </button>
              </div>
            </DropdownMenuItem>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>

    {/* Toggle sidebar */}
    <Button
      variant={filterSidebarVisible ? 'primary' : 'outline'}
      size="icon"
      onClick={() => setFilterSidebarVisible(v => !v)}
      title={filterSidebarVisible ? 'Ẩn bộ lọc' : 'Hiện bộ lọc'}
    >
      <SlidersHorizontal className="size-4" />
    </Button>

    {/* Primary Add */}
    <Button variant="primary" size="md" onClick={handleOpenAdd} title="Thêm mới (Ctrl + N)">
      <Plus className="size-4 mr-2" />
      Thêm mới
      <kbd className="ml-1.5 ...">Ctrl N</kbd>
    </Button>

    <KeyboardShortcutsHelp ... />
  </div>
</>
```

**Lưu ý**:
- w-[250px] (hoặc 300px tuỳ trang) cho search.
- `className="ps-9"` trên Input.
- My-filters luôn có Bookmark icon + logic restore default filter (useRef + useEffect).
- SlidersHorizontal button đổi variant khi active.

---

## 4. EnhancedDataGrid — Props chuẩn (sao chép nguyên)

```tsx
<EnhancedDataGrid
  table={table}
  wrapTableSection
  recordCount={filteredItems.length}
  cellOverflow="truncate"
  isLoading={isLoading}
  enableHorizontalScroll
  pinnedRightColumns={['actions']}
  tableLayout={{ rowBorder: true, headerBorder: true }}
  tableClassNames={{
    headerRow: '[&>th]:whitespace-nowrap',
  }}
  toolbar={ <> ... </> }
/>
```

### Giải thích các prop then chốt

- `wrapTableSection`: Bọc table trong border + rounded + bg-card + overflow hidden đúng.
- `cellOverflow="truncate"`: Cell không wrap chữ lung tung.
- `enableHorizontalScroll`: Bắt buộc khi có nhiều cột hoặc muốn actions luôn nhìn thấy.
- `pinnedRightColumns={['actions']}`: **BẮT BUỘC** cho cột Thao tác (actions). Component sẽ tự set columnPinning + enable scroll.
- `tableLayout={{ rowBorder: true, headerBorder: true }}`: Viền dòng + viền header.
- Component mặc định thêm `headerSticky: true`.
- `tableClassNames.headerRow`: Giữ header text không wrap.

**Thứ tự prop QUAN TRỌNG NHẤT (tránh lỗi duplicate attr)**:
Tất cả layout props (`wrapTableSection`, `cellOverflow`, `enableHorizontalScroll`, `pinned*`, `tableLayout`, `tableClassNames`, `recordCount`, `isLoading`...) **PHẢI đặt trước** các prop phức tạp như `renderExpandedRow`, `groupRowContent`, `onRowClick`...

Ví dụ sai (gây lỗi TS17001 khi edit sau):
```tsx
<EnhancedDataGrid
  table={table}
  renderExpandedRow={...}
  tableLayout={{...}}   {/* ← duplicate / late → lỗi */}
  pinnedRightColumns={...}
/>
```

---

## 5. Cột actions (bắt buộc)

Luôn là cột cuối cùng:

```tsx
{
  id: 'actions',
  header: () => <div className="text-right whitespace-nowrap">Thao tác</div>,
  meta: { headerTitle: 'Thao tác' },
  cell: ({ row }) => (
    <div className="flex items-center justify-end gap-2">
      <Button variant="outline" size="icon" className="w-8 h-8" onClick=...>
        <Pencil className="w-4 h-4 ..." />
      </Button>
      <Button variant="outline" size="icon" className="w-8 h-8" onClick=...>
        <Trash2 className="w-4 h-4 text-destructive" />
      </Button>
    </div>
  ),
  size: 90,
  enableSorting: false,
}
```

Sau đó:
- `pinnedRightColumns={['actions']}`
- `enableHorizontalScroll`

---

## 6. Loại B — Titled simple list (disposal-reason-list-page.tsx và tương tự)

Chỉ dùng khi **không** có advanced sidebar + my-filters.

```tsx
<Container className="h-full flex flex-col overflow-hidden">
  <div className="flex flex-col flex-1 gap-2 overflow-hidden min-h-0">
    <div className="flex-shrink-0">
      <Toolbar>
        <ToolbarHeading>
          <ToolbarPageTitle text="Lý do xuất huỷ/tặng/dùng" />
        </ToolbarHeading>
      </Toolbar>
    </div>

    <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
      <EnhancedDataGrid ... toolbar={search + add button} ... />
    </div>
  </div>
</Container>
```

**Khi convert từ Loại A sang B hoặc ngược lại**:
- Phải cân bằng số lượng `</div>`.
- Xóa `flex-1 min-h-0` wrapper + pe-1 pt-3.5 khi có title.
- Không để thừa `</div>` gây "closing tag for Container".

---

## 7. Overview / KPI (warehouse-overview-page + warehouse-overview-tab + stock-card-panel)

### Header (tabs trigger + refresh)

```tsx
<div className="flex items-center justify-between px-3 pt-2 shrink-0">
  <TabsList ... />
  <Button variant="outline" ...>Cập nhật</Button>
</div>
```

### Nội dung tab

```tsx
<div className="px-4 py-4 overflow-y-auto h-full space-y-4">
  {/* KPI strip */}
  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
    <KpiCard ... />
  </div>
  ...
</div>
```

### KpiCard chuẩn (copy nguyên từ warehouse-overview-tab.tsx)

```tsx
function KpiCard({ icon, label, value, sub, tone }: KpiCardProps) {
  const toneCls = {
    primary: 'bg-blue-50 text-blue-700 border-blue-100',
    info: 'bg-sky-50 text-sky-700 border-sky-100',
    warning: 'bg-amber-50 text-amber-700 border-amber-100',
    success: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    destructive: 'bg-red-50 text-red-700 border-red-100',
  }[tone]

  return (
    <Card className="p-0">
      <CardContent className="p-3">
        <div className="flex items-start gap-3">
          <div className={cn('rounded-md p-2 shrink-0 border-[0.5px]', toneCls)}>{icon}</div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-muted-foreground truncate">{label}</p>
            <p className="text-xl font-bold leading-tight truncate">{value}</p>
            {sub && <p className="text-[11px] text-muted-foreground truncate">{sub}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

Stock-card-panel copy y chang (SummaryKpi).

**Không** dùng Card p-4, padding khác, hoặc thiếu border-[0.5px] trên icon div.

---

## 8. Spacing & Padding Rules (bắt buộc)

- Loại A (không title): `pe-1 pt-3.5` trên div chứa grid.
- Khi sidebar mở: `gap-3`.
- Overview content: `px-4 py-4 space-y-4`.
- Header tabs/overview: `px-3 pt-2`.
- Search: w-[250px] hoặc 300px, ps-9.
- Không dùng `mt-2` sau title (hoặc sau filter area) trong các trang list filter.
- KPI grid: `gap-3`.
- Không có khoảng thừa giữa Toolbar/Search và table.

---

## 9. JSX Hygiene & Edit Safety Rules (ngăn lỗi tương lai)

1. **Thứ tự prop**: Tất cả props layout + table control (wrap, cellOverflow, enableHorizontalScroll, pinned*, tableLayout, tableClassNames, recordCount, isLoading, toolbar...) **đặt trước** renderExpandedRow / groupRowContent / onRowClick.
2. **Không duplicate attr**: Khi edit, không append prop sau render func.
3. **Nesting đếm div**: Khi bỏ title Toolbar để chuyển sang Loại A → xóa đúng wrapper div. Luôn verify bằng cách chạy tsc hoặc mở màn.
4. **Search không label**: Dùng div.relative + icon absolute + Input ps-9. Không `<label>`.
5. **Actions column**: Luôn `id: 'actions'`, pinnedRight, size hợp lý (~90), justify-end.
6. **Header text**: Dùng `whitespace-nowrap` trong header + tableClassNames headerRow.
7. **Container**: Luôn `h-full flex flex-col overflow-hidden` ở root. Grid area phải có `min-h-0 flex-1 overflow-hidden`.

---

## 10. Saved Filters & Keyboard (phần bắt buộc của Loại A)

- Master data: `UserScreenFilter` filtered by `ScreenCode` (Filter.ScreenCodes.XXX).
- Auto restore default filter bằng useRef + useEffect (chỉ 1 lần).
- useKeyboard cho Ctrl+N mở add (enabled khi !sheetOpen).
- Delete / set default filter gọi adapter + invalidate 'UserScreenFilter'.

---

## 11. Anti-patterns (Những gì từng gây lỗi)

- ❌ Thêm title Toolbar vào Loại A → thừa gap + mt thừa.
- ❌ `pinnedRightColumns` sau `renderExpandedRow` → duplicate prop lỗi TS.
- ❌ Bỏ title nhưng quên xóa 1 `</div>` → "closing tag for Container".
- ❌ Dùng `mt-2` hoặc gap-2 sai chỗ sau khi bỏ title.
- ❌ Search có `<label className="...">Tìm kiếm</label>` + Input thường → không khớp kho.
- ❌ Không pin actions → cột thao tác bị ẩn khi scroll.
- ❌ KpiCard: Card p-4 hoặc CardContent p-4 hoặc thiếu border-[0.5px] trên icon → lệch style.
- ❌ Thiếu `enableHorizontalScroll` khi có pinnedRight.
- ❌ Header không có `whitespace-nowrap` + tableClassNames → header wrap xấu.

---

## 12. Checklist khi tạo màn hình list mới

- [ ] Xác định Loại A hay B.
- [ ] Copy nguyên outer structure + min-h-0 + overflow từ inventory-list-page (Loại A).
- [ ] Search div + ps-9 + icon đúng.
- [ ] My-filters dropdown + Sliders + primary button đúng (nếu Loại A).
- [ ] `filterSidebarVisible` default false + conditional gap-3 + pe-1 pt-3.5.
- [ ] EnhancedDataGrid props đầy đủ + đúng thứ tự (layout trước).
- [ ] Cột actions + pinnedRightColumns + enableHorizontalScroll.
- [ ] tableLayout rowBorder + headerBorder.
- [ ] tableClassNames headerRow nếu cần.
- [ ] Overview: header px-3 pt-2, nội dung px-4 py-4 space-y-4 + KpiCard copy nguyên.
- [ ] Chạy tsc + mở màn hình verify không lỗi JSX, không thừa gap, actions pinned, scroll ngang, header sticky.

---

## 13. File tham chiếu (canonical source)

- **Loại A tốt nhất**: `worktrees/ipd-improve-v5/fe/src/modules/warehouse/pages/inventory/inventory-list-page.tsx`
- **Loại B titled**: `.../disposal-reason/disposal-reason-list-page.tsx`, `manual-adjustment-reason-list-page.tsx`
- **Overview + KpiCard**: `.../overview/warehouse-overview-page.tsx` + `warehouse-overview-tab.tsx`
- **Kpi reuse**: `.../stock-management/stock-card-panel.tsx`
- **Grid component**: `worktrees/ipd-improve-v5/fe/src/components/ui/enhanced-data-grid.tsx`
- Các trang khác trong warehouse/ và warehouse-transaction/ làm ví dụ phụ.

**Lưu ý**: Khi worktree thay đổi, pattern vẫn phải được copy từ các file này hoặc promote thành engine rule nếu ổn định.

---

## 14. Ghi chú bổ sung

- Pattern này đã được dùng để sửa hàng loạt màn hình: bed-management/*-list-page, inpatient-record, inpatient-reception, hospital-management (shift, department, price-list, schedule), examination, consultation, v.v.
- Mọi lần edit list page trong tương lai đều phải đối chiếu file này trước khi code.
- Nếu phát hiện lệch → cập nhật file này + fix nguồn.

**Đây là tài liệu sống. Cập nhật khi có biến thể được owner chấp nhận.**

---

*Distilled 2026-06 từ phân tích sâu module kho + hàng loạt lỗi thực tế ở các module nội trú/giường/lịch.*
