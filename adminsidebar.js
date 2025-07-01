const AdminSidebar = ({ menuConfig }) => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const [activeItemId, setActiveItemId] = useState(null)
  const [openSubmenus, setOpenSubmenus] = useState({})
  const [isCollapsed, setIsCollapsed] = useState(false)

  const initSidebar = useCallback(() => {
    // restore collapse state
    try {
      const saved = localStorage.getItem('adminSidebarCollapsed')
      if (saved !== null) {
        setIsCollapsed(JSON.parse(saved))
      }
    } catch (e) {
      console.error('Failed to parse sidebar collapse state', e)
      setIsCollapsed(false)
    }

    // determine active item and which submenus to open
    const path = location.pathname
    let active = null
    const submenusToOpen = {}

    const findActive = items => {
      for (const item of items) {
        if (item.route === path) {
          active = item.id
          return true
        }
        if (item.subItems) {
          if (findActive(item.subItems)) {
            submenusToOpen[item.id] = true
            return true
          }
        }
      }
      return false
    }

    findActive(menuConfig)
    setOpenSubmenus(submenusToOpen)
    if (active) {
      setActiveItemId(active)
    }
  }, [location.pathname, menuConfig])

  useEffect(() => {
    initSidebar()
  }, [initSidebar])

  useEffect(() => {
    try {
      localStorage.setItem('adminSidebarCollapsed', JSON.stringify(isCollapsed))
    } catch (e) {
      console.error('Failed to save sidebar collapse state', e)
    }
  }, [isCollapsed])

  const handleItemClick = item => {
    if (item.subItems) {
      setOpenSubmenus(prev => ({ ...prev, [item.id]: !prev[item.id] }))
    } else if (item.route) {
      navigate(item.route)
    }
    setActiveItemId(item.id)
  }

  const renderMenu = (items, level = 0) => (
    <ul className={`sidebar-menu level-${level}`}>
      {items.map(item => {
        const isActive = item.id === activeItemId
        const isOpen = !!openSubmenus[item.id]
        return (
          <li key={item.id} className={`menu-item${isActive ? ' active' : ''}`}>
            <button
              type="button"
              className="menu-link"
              onClick={() => handleItemClick(item)}
              aria-expanded={item.subItems ? isOpen : undefined}
              aria-current={item.route && isActive ? 'page' : undefined}
            >
              {item.icon && <span className="menu-icon">{item.icon}</span>}
              {!isCollapsed && <span className="menu-text">{t(item.label)}</span>}
              {item.subItems && !isCollapsed && (
                <span className="submenu-arrow">{isOpen ? '?' : '?'}</span>
              )}
            </button>
            {item.subItems && isOpen && renderMenu(item.subItems, level + 1)}
          </li>
        )
      })}
    </ul>
  )

  return (
    <aside className={`admin-sidebar${isCollapsed ? ' collapsed' : ''}`}>
      <div className="sidebar-header">
        {!isCollapsed && <h1 className="sidebar-title">{t('Admin Panel')}</h1>}
        <button
          type="button"
          className="collapse-btn"
          aria-label={isCollapsed ? t('Expand sidebar') : t('Collapse sidebar')}
          onClick={() => setIsCollapsed(prev => !prev)}
        >
          {isCollapsed ? '?' : '?'}
        </button>
      </div>
      <nav className="sidebar-nav">{renderMenu(menuConfig)}</nav>
    </aside>
  )
}

const menuItemShape = {
  id: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  icon: PropTypes.node,
  route: PropTypes.string,
}

AdminSidebar.propTypes = {
  menuConfig: PropTypes.arrayOf(
    PropTypes.shape({
      ...menuItemShape,
      subItems: PropTypes.arrayOf(
        PropTypes.shape({
          ...menuItemShape,
          subItems: PropTypes.array, // further nesting allowed
        })
      ),
    })
  ).isRequired,
}

export default AdminSidebar