import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Box,
  CssBaseline,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
} from '@mui/material';
import {
  Menu as MenuIcon,
  LayoutDashboard,
  FolderOpen,
  Server,
  ShieldAlert,
  Activity,
  AlertTriangle,
  GitBranch,
  FileText,
  Settings,
  LogOut,
  UploadCloud
} from 'lucide-react';

const drawerWidth = 260;

const menuItems = [
  { text: 'Dashboard', icon: <LayoutDashboard size={20} />, path: '/dashboard' },
  { text: 'Projects', icon: <FolderOpen size={20} />, path: '/projects' },
  { text: 'Deployments', icon: <Server size={20} />, path: '/environment' }, // re-using environment page for deployments list for now
  { text: 'Findings', icon: <ShieldAlert size={20} />, path: '/findings' },
  { text: 'Risk Forecast', icon: <Activity size={20} />, path: '/risk' },
  { text: 'Threat Alerts', icon: <AlertTriangle size={20} />, path: '/threats' },
  { text: 'Traces', icon: <GitBranch size={20} />, path: '/traces' },
  { text: 'Reports', icon: <FileText size={20} />, path: '/reports' },
  { text: 'Settings', icon: <Settings size={20} />, path: '/settings' },
];

export default function DashboardLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleNavigation = (path: string) => {
    navigate(path);
    setMobileOpen(false);
  };

  const drawer = (
    <div className="flex flex-col h-full bg-slate-900 text-slate-300">
      <div className="p-6 flex items-center space-x-3">
        <div className="w-8 h-8 bg-indigo-500 rounded flex items-center justify-center font-bold text-white shadow-lg">P2</div>
        <Typography variant="h6" noWrap className="font-bold text-white tracking-tight text-lg">
          P2DP Platform
        </Typography>
      </div>
      <List className="flex-1 px-4 space-y-1 py-0">
        {menuItems.map((item) => {
          const isActive = location.pathname.startsWith(item.path);
          return (
            <ListItem key={item.text} disablePadding>
              <ListItemButton
                onClick={() => handleNavigation(item.path)}
                className={`rounded-md transition-colors ${
                  isActive ? 'bg-indigo-600 text-white' : 'hover:bg-slate-800 hover:text-white text-slate-400'
                }`}
                sx={{ minHeight: 36, px: 1.5, py: 1 }}
              >
                <ListItemIcon sx={{ minWidth: 'auto', mr: 1.5, opacity: 0.7 }} className={isActive ? 'text-white' : 'text-slate-400'}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText 
                  disableTypography
                  primary={
                    <Typography sx={{ fontSize: '0.875rem', fontWeight: isActive ? 500 : 500 }}>
                      {item.text}
                    </Typography>
                  } 
                />
                {item.text === 'Findings' && (
                  <span className="ml-auto bg-rose-500 text-[10px] px-1.5 rounded-full text-white font-semibold">12</span>
                )}
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
      <div className="p-4 mt-auto border-t border-slate-800">
        <ListItem disablePadding>
          <ListItemButton onClick={() => navigate('/settings')} className="rounded-md hover:bg-slate-800 hover:text-white text-slate-400 transition-colors" sx={{ minHeight: 36, px: 1.5, py: 1 }}>
            <ListItemIcon sx={{ minWidth: 'auto', mr: 1.5, opacity: 0.7 }} className="text-slate-400">
              <Settings size={20} />
            </ListItemIcon>
            <ListItemText 
              disableTypography 
              primary={
                <Typography sx={{ fontSize: '0.875rem', fontWeight: 500 }}>
                  Settings
                </Typography>
              } 
            />
          </ListItemButton>
        </ListItem>
        <ListItem disablePadding>
          <ListItemButton onClick={() => { localStorage.removeItem('token'); navigate('/login'); }} className="rounded-md hover:bg-slate-800 hover:text-white text-slate-400 transition-colors mt-1" sx={{ minHeight: 36, px: 1.5, py: 1 }}>
            <ListItemIcon sx={{ minWidth: 'auto', mr: 1.5, opacity: 0.7 }} className="text-slate-400">
              <LogOut size={20} />
            </ListItemIcon>
            <ListItemText 
              disableTypography 
              primary={
                <Typography sx={{ fontSize: '0.875rem', fontWeight: 500 }}>
                  Sign Out
                </Typography>
              } 
            />
          </ListItemButton>
        </ListItem>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-slate-50 font-sans text-slate-900 overflow-hidden">
      <CssBaseline />
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
          bgcolor: 'white',
          borderBottom: '1px solid',
          borderColor: '#e2e8f0', // slate-200
          boxShadow: 'none',
        }}
      >
        <Toolbar sx={{ minHeight: '56px !important' }} className="px-6">
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' }, color: '#64748b' }}
          >
            <MenuIcon />
          </IconButton>
          <div className="flex flex-1 items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-widest hidden sm:block">Workspace</div>
              <div className="h-4 w-px bg-slate-200 hidden sm:block"></div>
              <div className="flex items-center font-medium text-slate-700">
                {menuItems.find(i => location.pathname.startsWith(i.path))?.text || 'P2DP'}
                <span className="ml-2 text-[10px] bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full hidden sm:block">Active</span>
              </div>
            </div>
            
            <div className="flex items-center space-x-6">
              <div className="relative cursor-pointer hidden sm:block">
                <span className="absolute -top-1 -right-1 w-2 h-2 bg-rose-500 rounded-full ring-2 ring-white"></span>
                <span className="text-slate-400">🔔</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-[10px] font-bold">ME</div>
                <span className="text-sm font-medium text-slate-600 hidden sm:block">Admin</span>
              </div>
            </div>
          </div>
        </Toolbar>
      </AppBar>
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
        aria-label="mailbox folders"
      >
        {/* Mobile drawer */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, 
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        {/* Desktop drawer */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth, borderRight: 'none' },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{ flexGrow: 1, p: { xs: 2, md: 4 }, width: { sm: `calc(100% - ${drawerWidth}px)` }, mt: '56px', overflowY: 'auto' }}
        className="bg-slate-50"
      >
        <div className="max-w-7xl mx-auto pb-12">
          <Outlet />
        </div>
      </Box>
    </div>
  );
}
