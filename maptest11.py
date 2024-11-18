# -*- coding: utf-8 -*-
"""
Created on Tue Sep 17 08:45:57 2024

@author: e873582
"""
from folium.plugins import BeautifyIcon #function to create custom icon
import pandas as pd
import avangrid_databases as adb
import geopandas as gpd
import GISRestAPI as gis
import streamlit as st
from streamlit_folium import folium_static
import folium
import matplotlib.pyplot as plt

#%% build circuit style
def circstyle(feature):
        
        overunder = feature['properties']['OVERUNDER']
        numphases = feature['properties']['NUMPHASES']
        #print(f"NUMPHASES: {numphases}, OVERUNDER: {overunder}")
        numphases = int(numphases)
        if numphases == 1:
            color = 'blue'
        elif numphases == 2:
            color = 'green'
        elif numphases == 3:
             color = 'red'   
        else:
            color = 'orange'
        #color = "#118DFF" if main_or_tie == 'MAIN' else "#E66C37"
        dash_array = '6' if overunder == 'U' else None
        #print(f"Color: {color}, Dash Array: {dash_array}")
        return {'color':color,'dashArray':dash_array}





#%% build recloser
def build_recloser(circ):
    query_recloser = f'''SELECT CIRCUIT, TYPE, NAME, Latitude, Longitude
                         FROM [UAD].[Inputs].[GIS_ScadaDevices] 
                         WHERE CIRCUIT = '{circ}' '''
    
    dfrecl = adb.query(query_recloser, 'UAD')
    dfrecl = gpd.GeoDataFrame(dfrecl, geometry=gpd.points_from_xy(dfrecl.Longitude, dfrecl.Latitude), crs="EPSG:4326")
    
    return dfrecl
# def build_recloser(circ):
#     query_recloser = '''SELECT CIRCUIT, TYPE, NAME, Latitude,longitude
#     FROM [UAD].[Inputs].[GIS_ScadaDevices] WHERE CIRCUIT = '{%s}' '''%circ
    
#     dfrecl = adb.query(build_recloser, 'UAD')
#     dfrecl = gpd.GeoDataFrame(dfrecl, geometry=gpd.points_from_xy(dfrecl.Longitude, dfrecl.Latitude), crs="EPSG:4326")
    
#     return dfrecl
#%% build device
def build_device(circ):
    query_device = '''SELECT LEGACYPOLE, FUSESIZE, CIRCUIT, Latitude, Longitude, TYPE
    FROM [UAD].[Inputs].[GIS_Devices_SMWeb]
    WHERE CIRCUIT = '{0}'
    GROUP BY Circuit, CIRCUIT, LEGACYPOLE, FUSESIZE, Latitude, Longitude, TYPE'''.format(circ)

    # Execute the query
    dfdevice = adb.query(query_device, 'UAD')

    # Convert to GeoDataFrame
    dfdevice = gpd.GeoDataFrame(
        dfdevice, geometry=gpd.points_from_xy(dfdevice.Longitude, dfdevice.Latitude), crs="EPSG:4326"
    )

    # Remove rows with null latitude values
    dfdevice = dfdevice[~dfdevice['Latitude'].isnull()].reset_index(drop=True)

    return dfdevice






#%% build outage


def build_outage(circ):
    query2 = ''' select Incident,Duration,CustomerCount,Circuit,CauseDesc,CauseText,FaultRoad,Comments,YYYY,faultlatitude,
    faultlongitude,MainCause,FaultPole,Mod_PSC_Cause
                  from uod.dbo.outages 
                  where yyyy > '2019'  and Circuit ='%s' and CustomerCount >1 ''' %circ
    df2 = adb.query(query2, 'UOD')
    df2=pd.DataFrame(df2)
    df_new = df2[~(df2['faultlatitude'].isnull())].reset_index().drop(columns =['index'])
    
    #df2=df_new
    #gdf2 = gis.gdf_from_sql(df2)
    #gdf2 = gpd.GeoDataFrame(df_new, geometry=gpd.points_from_xy(df2.faultlongitude, df2.faultlatitude), crs="EPSG:4326")
    gdf2 = gpd.GeoDataFrame(df_new, geometry=gpd.points_from_xy(df_new.faultlongitude, df_new.faultlatitude), crs="EPSG:4326")
    return gdf2
    
    

#%% DEFINING FUNCTION TO BUILD CIRCUIT GEODATAFRAME
def build_circuit(circ):
    
    query = ''' SELECT OPCO, CIRCUIT, LINETYPE,NUMPHASES,OVERUNDER, Z_GISIDTO, Z_GISIDFRO, LATTO,LATFROM, LONGTO, LONGFROM,GISID 
        FROM [UAD].[Inputs].[GIS_Circuits_SMWeb]
        WHERE CIRCUIT = '%s'and LINETYPE not in ('TAP WIRE','SECONDARY')
        and VOLTAGE > 0
        ''' %circ
    
    df = adb.query(query, 'UAD')
   
    gdf = gis.gdf_from_sql(df)
    
    return gdf

#%% DEFINING FUNCTION TO PULL LIST OF CIRCUITS
def list_circ(opco):
    
    query = ''' SELECT DISTINCT CIRCUIT
                FROM UOD.DBO.REFCIRCUITS
                WHERE OPCO = '%s' ''' % opco
    df = adb.query(query, 'UOD')
    return df
#%% Substation
def fetch_substation(circ):

    query_sub = ''' select rc.substname,rc.circuit, s.LATITUDE, s.LONGITUDE
                    from uod.dbo.refCircuits rc left join uad.gis.Substations s ON
                    rc.substname = s.NAME
                    where rc.circuit = '%s' 
                ''' %circ

    df = adb.query(query_sub,'UAD')
    
    df = df.rename(columns = {'LATITUDE': 'Latitude','LONGITUDE':'Longitude'})
    
    df= gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude), crs="EPSG:4326"
    )
    
    if df['Latitude'].iloc[0]:
        gis.populate_googleMaps_ArcFM_web(df, opco = 'CMP',html = True)
    
    df = df.rename(columns = {'substname':'Substation','circuit':'Circuit','Latitude': 'LATITUDE','Longitude':'LONGITUDE'})
    
    return df

#%% STARTING STREAMLIT APPLICATION

# setup streamlit page to a wide layout
st.set_page_config(layout='wide')

# add subheader CIRCUIT MAP
st.subheader('CIRCUIT MAP')

# defining OPCO
opco = st.selectbox('SELECT OPCO', ['NYSEG', 'RGE'], index=None)

# condition check whether OPCO was selected or not
if opco is None:
    st.stop()
else:
    # pulling circuit list
    df_circ = list_circ(opco)
    
    # selecting circuit
    circ = st.selectbox('SELECT CIRCUIT', df_circ['CIRCUIT'], index=None)
    
    # condition check whether CIRCUIT was selected or not
    if circ is None:
        st.stop()
    else:
        gdf2 = build_outage(circ)
        gdf = build_circuit(circ)
        print(gdf)
        df= fetch_substation(circ)
        gdf3=build_device(circ)
        gdf4= build_recloser(circ)
        #dfsub=outage_merge(circ)
        #df4= outage_merge(circ)
        #dfsub=outage_merge(circ)
        if gdf2.empty  :
            st.write("No data available for the selected circuit.")
            centroid = gdf.geometry.centroid

            # Extract the coordinates of the centroid
            centroid_coords = [centroid.y.mean(), centroid.x.mean()]

            # Create a Folium map centered at the centroid
            map = folium.Map(location=centroid_coords, zoom_start=16)

            #gdf['LATTO'] = gdf['LATTO'].astype(float)
            #gdf['LONGTO'] = gdf['LONGTO'].astype(float)
        
            #map= folium.Map(location=[gdf.LONGTO.mean(), gdf.LATTO.mean()], zoom_start=12)
            gdf.explore(name='Circuit Segments',m=map,style_kwds=dict(style_function=circstyle))
            
            folium.LayerControl().add_to(map)
            
            
        else:
            
            map = folium.Map(location=[gdf2.geometry.y.mean(), gdf2.geometry.x.mean()], zoom_start=12)
            
             
ss_group = folium.FeatureGroup("Substations").add_to(map)
        #     for index,row in dfsub.iterrows():
        #         loc = (row['Latitude'], row['Longitude'])
        # #Creating icons
        #from folium.plugins import BeautifyIcon #function to create custom icon
ss_icon = BeautifyIcon(icon='house',inner_icon_style='color:#f2133c;font-size:20px;text-align:center;vertical-align:text-top;text-shadow: -1px 1px #000000, 1px 1px #000000, 1px -1px #000000,-1px -1px #000000;',
background_color='transparent',border_color='transparent',)
folium.Marker( icon=ss_icon,opacity= 0.9,location=[df.LATITUDE,df.LONGITUDE]).add_to(ss_group)
        # #Creating label
        #Simple version:
for index, row in df.iterrows():
         loc = (row['LATITUDE'], row['LONGITUDE'])    
         ss_html = f'''<strong>
                <span style="size: 8px;"> 
                                  {row['Substation']} 
                </span>
                </strong>'''
        # #background color altering: 
        #         ss_html = f'''<strong>
        #         <span style="size: 8px; background-color: {row['Operated']}; ">
        #                     {row['SUBSTNAME']} 
        #         </span>
        #         </strong>'''
from folium.features import DivIcon #function to create an html icon
folium.map.Marker(location=loc,icon=DivIcon(icon_size=(50,10),icon_anchor=(-10,5),html=ss_html)).add_to(ss_group)
gdf.explore(name='Circuit Segments',m=map,style_kwds=dict(style_function=circstyle))    
    #add outage icons
    #example of creating icons for each cause
gdf2['CustomIcon'] = None
gdf2.loc[gdf2['Mod_PSC_Cause']=='Tree Contacts', 'CustomIcon'] = 'tree'
gdf2.loc[gdf2['Mod_PSC_Cause']=='Company Equipment', 'CustomIcon'] = 'explosion'
gdf2.loc[gdf2['Mod_PSC_Cause']=='Accident (MVA)', 'CustomIcon'] = 'car'
gdf2.loc[gdf2['Mod_PSC_Cause']=='Animal Contact', 'CustomIcon'] = 'crow'
gdf2.loc[gdf2['Mod_PSC_Cause']=='Customer Equipment', 'CustomIcon'] = 'wrench'
gdf2.loc[gdf2['Mod_PSC_Cause']=='Lightning', 'CustomIcon'] = 'bolt'
gdf2.loc[gdf2['Mod_PSC_Cause']=='Non Utility Control', 'CustomIcon'] = 'clipboard'
gdf2.loc[gdf2['Mod_PSC_Cause']=='Operating Error', 'CustomIcon'] = 'person'
gdf2.loc[gdf2['Mod_PSC_Cause']=='Overloads', 'CustomIcon'] = 'lightbulb-slash'
gdf2.loc[gdf2['Mod_PSC_Cause']=='Planned', 'CustomIcon'] = 'traffic-cone'
gdf2.loc[gdf2['Mod_PSC_Cause']=='Unknown', 'CustomIcon'] = 'question'
out_group = folium.FeatureGroup("Outages").add_to(map)
print(gdf2)
for index,row in gdf2.iterrows():
                loc = (row['faultlatitude'],row['faultlongitude'])
                #HTML format of tooltip
                outtooltip = f'''<strong>Incident:</strong> {row['Incident']}<br>

<strong>CustomerCount:</strong> {row['CustomerCount']}<br>
<strong>CauseDesc:</strong> {row['CauseDesc']}<br>
<strong>Comments:</strong> {row['Comments']}<br>
<strong>MainCause:</strong> {row['MainCause']}'''
                out_icon = BeautifyIcon(icon=row['CustomIcon'],inner_icon_style='color:#063d04;font-size:20px;text-align:center;vertical-align:text-top;text-shadow: -1px 1px #ffff00, 1px 1px #ffff00, 1px -1px #ffff00,-1px -1px #ffff00;',
                                        background_color='transparent',border_color='transparent',)
                folium.Marker( icon=out_icon,opacity= 0.8,location=loc,tooltip=outtooltip).add_to(out_group)
device_group = folium.FeatureGroup("Fuses").add_to(map)

recl_group = folium.FeatureGroup("Recloser").add_to(map)
# Add custom icons based on the TYPE column
gdf3['CustomIcon'] = None
gdf3.loc[gdf3['TYPE'] == 'FUSE/CUTOUT', 'CustomIcon'] = 'florin-sign'
#gdf3.loc[gdf3['TYPE'] == 'RECLOSER', 'CustomIcon'] = 'square'
gdf3 = gdf3[~(gdf3['CustomIcon'].isnull())].reset_index().drop(columns =['index'])
# Debugging: Print the DataFrame to check the CustomIcon column
#print(gdf3[['Latitude', 'Longitude', 'TYPE', 'CustomIcon']])

for index, row in gdf3.iterrows():
    loc = (row['Latitude'], row['Longitude'])
    # HTML format of tooltip
    outtooltip = f'''<strong>{row['LEGACYPOLE']}:</strong> {row['TYPE']}<br>
    <strong>{row['CIRCUIT']}:</strong> {row['FUSESIZE']}<br>'''
    out_icon = BeautifyIcon(icon=row['CustomIcon'], inner_icon_style='color:#340ff2;font-size:15px;text-align:center;vertical-align:text-top;text-shadow: -1px 1px #ffff00, 1px 1px #ffff00, 1px -1px #ffff00,-1px -1px #ffff00;',
                            background_color='transparent', border_color='transparent')
    marker = folium.Marker(icon=out_icon, opacity=0.8, location=loc, tooltip=outtooltip).add_to(device_group)




gdf4['CustomIcon'] = None
gdf4.loc[gdf4['TYPE'] == 'SWITCH', 'CustomIcon'] = 'square'
gdf4.loc[gdf4['TYPE'] == 'RECLOSER', 'CustomIcon'] = 'square-rss'
gdf4 = gdf4[~(gdf4['CustomIcon'].isnull())].reset_index().drop(columns =['index'])
# Debugging: Print the DataFrame to check the CustomIcon column
#print(gdf4[['Latitude', 'Longitude', 'TYPE', 'CustomIcon']])

for index, row in gdf4.iterrows():
    loc = (row['Latitude'], row['Longitude'])
    # HTML format of tooltip
    outtooltip = f'''<strong>{row['CIRCUIT']}:</strong> {row['TYPE']}<br>
    <strong>{row['NAME']}:</strong><br>'''
    out_icon = BeautifyIcon(icon=row['CustomIcon'], inner_icon_style='color:#340ff2;font-size:15px;text-align:center;vertical-align:text-top;text-shadow: -1px 1px #ffff00, 1px 1px #ffff00, 1px -1px #ffff00,-1px -1px #ffff00;',
                            background_color='transparent', border_color='transparent')
    marker = folium.Marker(icon=out_icon, opacity=0.8, location=loc, tooltip=outtooltip).add_to(recl_group)
    #marker.add_to(map)            
            #Circuit_layer = folium.FeatureGroup(name='Circuit')
#gdf.explore(name='Circuit',m=map,column='NUMPHASES',cmap=('red','green','blue'),style_kwds={'weight': 3})
#gdf2.explore(name='Outage',m=map,column='CustomerCount',cmap='plasma', marker_kwds={'radius': 6})
            #gdf3.explore(name='Substation',m=map, marker_kwds={'radius': 8,'color':'red'})
            #gdf3.explore(name='Substation',m=map, marker_type='marker', marker_kwds={'color':'red'})
        #gdf3.explore(name='Substation', m=map, marker_type='marker', marker_kwds={'color': 'red'})
            #Circuit_layer.add_to(map)
            #gdf4.explore(name='groupoutage',m=map,)
           
folium.LayerControl().add_to(map)
            
            # create st_data object to display folium map
            #st_data = folium_static(map, width=800, height=800)
            #st.table(gdf2.drop(columns='geometry'))
col1, col2 = st.columns([3, 3])

with col1:
    st.dataframe(gdf2.drop(columns='geometry'))
with col2:
    folium_static(map)
#st.dataframe(dfsub)    