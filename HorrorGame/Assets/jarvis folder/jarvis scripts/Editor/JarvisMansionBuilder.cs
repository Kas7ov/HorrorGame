using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace JarvisMansion.Editor
{
    // One-time scene creation. Never opens a scene in Single mode or saves the user's scene.
    [InitializeOnLoad]
    public static class JarvisMansionBuilder
    {
        const string Root = "Assets/jarvis folder";
        const string ScenePath = Root + "/jarvis scenes/Jarvis_Manor.unity";
        const string MeshPath = Root + "/jarvis models/Manor_Meshes.asset";
        static readonly Dictionary<string, Mesh> meshCache = new Dictionary<string, Mesh>();
        static readonly Dictionary<string, Material> materials = new Dictionary<string, Material>();
        static int count, tempLayer = 30;
        static Transform shell, interiors, grounds, fixtures;
        static Scene builtScene;
        static bool busy;
        static JarvisMansionBuilder() { EditorApplication.delayCall += TryBuild; }
        static void TryBuild()
        {
            if (busy || File.Exists(ScenePath) || File.Exists(Root + "/jarvis docs/BuildFailed.txt")) return;
            if (EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling || EditorApplication.isUpdating)
            { EditorApplication.delayCall += TryBuild; return; }
            Build();
        }
        public static void Build()
        {
            if (busy || File.Exists(ScenePath)) return;
            busy = true;
            Scene previous = SceneManager.GetActiveScene();
            var previousSelection = Selection.objects;
            try
            {
                foreach (string folder in new[] { "jarvis scenes", "jarvis materials", "jarvis models", "jarvis textures", "jarvis previews", "jarvis docs" })
                    Directory.CreateDirectory(Root + "/" + folder);
                AssetDatabase.Refresh();
                builtScene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
                SceneManager.SetActiveScene(builtScene);
                shell = Group("01 MANSION | shell, roof and stairs"); interiors = Group("02 ROOMS | furniture and panelling");
                grounds = Group("03 GROUNDS | gate, path and trees"); fixtures = Group("04 ATMOSPHERE | lights and clouds");
                MakeMaterials(); Exterior(); FloorsAndRooms(); Staircase(); Furnish(); Garden();
                VolumeProfile profile = Atmosphere(); Camera player = Explorer();
                Physics.SyncTransforms();
                // Own temporary culling layer isolates offscreen previews from the user's loaded scene.
                foreach (var go in builtScene.GetRootGameObjects()) SetLayer(go, tempLayer);
                // No automatic GPU previews: HDRP/D3D12 render requests proved unstable
                // while the user's other scene was loaded. Save and validate only.
                foreach (var go in builtScene.GetRootGameObjects()) SetLayer(go, 0);
                EditorSceneManager.SaveScene(builtScene, ScenePath);
                File.WriteAllText(Root + "/jarvis docs/BuildStatus.txt", "Scene saved. GPU previews disabled.");
                foreach (var go in builtScene.GetRootGameObjects()) SetLayer(go, 0);
                player.cullingMask = -1; player.GetComponent<HDAdditionalCameraData>().volumeLayerMask = 1;
                EditorSceneManager.MarkSceneDirty(builtScene); EditorSceneManager.SaveScene(builtScene, ScenePath);
                AssetDatabase.SaveAssets();
                string report = "{\n  \"unity\": \"" + Application.unityVersion + "\",\n  \"scene\": \"" + ScenePath + "\",\n  \"objects\": " + count + ",\n  \"uniqueMeshes\": " + meshCache.Count + ",\n  \"materials\": " + materials.Count + ",\n  \"cloudLayer\": true,\n  \"sharedPipelineModified\": false,\n  \"twoFloors\": true,\n  \"playerController\": true,\n  \"existingSceneSaved\": false\n}";
                File.WriteAllText(Root + "/jarvis docs/BuildReport.json", report);
                File.WriteAllText(Root + "/jarvis docs/BuildStatus.txt", "Complete: Jarvis_Manor.unity saved. Existing scene restored without saving it.");
                Debug.Log("[Jarvis] Mansion complete: " + ScenePath);
            }
            catch (Exception e)
            {
                Directory.CreateDirectory(Root + "/jarvis docs");
                File.WriteAllText(Root + "/jarvis docs/BuildFailed.txt", e.ToString()); Debug.LogException(e);
            }
            finally
            {
                if (previous.IsValid() && previous.isLoaded) SceneManager.SetActiveScene(previous);
                if (builtScene.IsValid() && builtScene.isLoaded) EditorSceneManager.CloseScene(builtScene, true);
                Selection.objects = previousSelection; busy = false;
            }
        }
        static GameObject New(string name, Transform parent = null)
        {
            var go = new GameObject(name); SceneManager.MoveGameObjectToScene(go, builtScene);
            go.layer = tempLayer; if (parent) go.transform.SetParent(parent, false); count++; return go;
        }
        static Transform Group(string name) { return New(name).transform; }
        static void SetLayer(GameObject go, int layer) { foreach (Transform t in go.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = layer; }
        static Mesh SaveMesh(Mesh mesh, string key)
        {
            mesh.name = key;
            if (!File.Exists(MeshPath)) AssetDatabase.CreateAsset(mesh, MeshPath); else AssetDatabase.AddObjectToAsset(mesh, MeshPath);
            meshCache[key] = mesh; return mesh;
        }
        static Mesh BoxMesh(Vector3 s)
        {
            string key = "Box " + s.ToString("F3"); if (meshCache.TryGetValue(key, out var found)) return found;
            Vector3 h = s * .5f; var v = new List<Vector3>(); var uv = new List<Vector2>(); var tri = new List<int>();
            void Face(Vector3 a, Vector3 b, Vector3 c, Vector3 d)
            {
                int n = v.Count; v.AddRange(new[] { a, b, c, d });
                float w = Vector3.Distance(a,b), height = Vector3.Distance(b,c);
                uv.AddRange(new[] { Vector2.zero, new Vector2(w,0), new Vector2(w,height), new Vector2(0,height) });
                tri.AddRange(new[] { n,n+1,n+2,n,n+2,n+3 });
            }
            Face(new Vector3(-h.x,-h.y,-h.z),new Vector3(-h.x,h.y,-h.z),new Vector3(h.x,h.y,-h.z),new Vector3(h.x,-h.y,-h.z));
            Face(new Vector3(h.x,-h.y,h.z),new Vector3(h.x,h.y,h.z),new Vector3(-h.x,h.y,h.z),new Vector3(-h.x,-h.y,h.z));
            Face(new Vector3(-h.x,-h.y,h.z),new Vector3(-h.x,h.y,h.z),new Vector3(-h.x,h.y,-h.z),new Vector3(-h.x,-h.y,-h.z));
            Face(new Vector3(h.x,-h.y,-h.z),new Vector3(h.x,h.y,-h.z),new Vector3(h.x,h.y,h.z),new Vector3(h.x,-h.y,h.z));
            Face(new Vector3(-h.x,h.y,-h.z),new Vector3(-h.x,h.y,h.z),new Vector3(h.x,h.y,h.z),new Vector3(h.x,h.y,-h.z));
            Face(new Vector3(-h.x,-h.y,h.z),new Vector3(-h.x,-h.y,-h.z),new Vector3(h.x,-h.y,-h.z),new Vector3(h.x,-h.y,h.z));
            var m = new Mesh(); m.SetVertices(v);m.SetUVs(0,uv);m.SetTriangles(tri,0);m.RecalculateNormals();m.RecalculateBounds();return SaveMesh(m,key);
        }
        static GameObject Box(string name, Vector3 pos, Vector3 size, string material, Transform parent = null, bool collider = true)
        {
            var go = New(name,parent ?? shell); go.transform.position=pos; go.AddComponent<MeshFilter>().sharedMesh=BoxMesh(size);
            go.AddComponent<MeshRenderer>().sharedMaterial=materials[material]; if(collider) go.AddComponent<BoxCollider>().size=size; return go;
        }
        static GameObject Beam(string name, Vector3 a, Vector3 b, float width, string mat, Transform parent, bool collider = false)
        {
            var go=Box(name,(a+b)*.5f,new Vector3(width,Vector3.Distance(a,b),width),mat,parent,collider);
            go.transform.rotation=Quaternion.FromToRotation(Vector3.up,b-a);return go;
        }
        static void MakeMaterials()
        {
            Material Mat(string name, Color color, float smooth=0, int pattern=0)
            {
                var m = new Material(Shader.Find("HDRP/Lit"));m.name=name;m.SetColor("_BaseColor",color);m.SetFloat("_Smoothness",smooth);m.enableInstancing=true;
                if(pattern>0)
                {
                    int n=256;var t=new Texture2D(n,n,TextureFormat.RGBA32,true);t.name=name+" surface";t.wrapMode=TextureWrapMode.Repeat;
                    var pixels=new Color[n*n];
                    for(int y=0;y<n;y++)for(int x=0;x<n;x++)
                    {
                        float a=Mathf.PerlinNoise(x*.11f+pattern*17,y*.13f)*.2f+.82f;
                        if(pattern==1){int row=y/32;int xx=(x+(row%2)*32)%64; if(y%32<3||xx<3)a=.44f;else a*=.9f+.2f*Mathf.PerlinNoise((x+(row%2)*32)/64, row*3.17f);}
                        if(pattern==2){if(x%32<2)a=.32f;else a*=.78f+.22f*Mathf.PerlinNoise(x*.35f,y*.02f);if(y%128<2)a*=.65f;}
                        if(pattern==3){int xx=(x+((y/32)%2)*16)%32;if(y%32<2||xx<2)a=.35f;}
                        if(pattern==4){float mark=Mathf.Abs(Mathf.Sin(x*Mathf.PI/32)*Mathf.Sin(y*Mathf.PI/32));a*=.70f+.3f*mark; a*=.75f+.25f*Mathf.PerlinNoise(x*.03f,y*.027f);}
                        pixels[y*n+x]=new Color(a,a,a,1);
                    }
                    t.SetPixels(pixels);t.Apply();AssetDatabase.CreateAsset(t,Root+"/jarvis textures/"+t.name+".asset");m.SetTexture("_BaseColorMap",t);
                }
                HDMaterial.ValidateMaterial(m);AssetDatabase.CreateAsset(m,Root+"/jarvis materials/"+name+".mat");materials[name]=m;return m;
            }
            Mat("Weathered limestone",new Color(.43f,.43f,.38f),.08f,1);Mat("Foundation stone",new Color(.21f,.23f,.22f),.05f,1);
            Mat("Old plaster",new Color(.43f,.40f,.32f),.03f,4);Mat("Mahogany",new Color(.16f,.075f,.041f),.22f,2);
            Mat("Oak floor",new Color(.25f,.15f,.082f),.25f,2);Mat("Slate roof",new Color(.075f,.105f,.13f),.18f,3);
            Mat("Iron",new Color(.027f,.032f,.034f),.28f);Mat("Aged brass",new Color(.34f,.23f,.075f),.50f);
            Mat("Burgundy velvet",new Color(.19f,.025f,.035f),.08f);Mat("Dusty linen",new Color(.5f,.47f,.37f),.02f);
            Mat("Damp grass",new Color(.075f,.11f,.057f),.03f,4);Mat("Gravel",new Color(.19f,.20f,.18f),.02f,1);
            Mat("Book red",new Color(.22f,.055f,.042f));Mat("Book green",new Color(.06f,.13f,.105f));Mat("Book brown",new Color(.22f,.15f,.07f));
            var glass=Mat("Smoky window glass",new Color(.14f,.21f,.23f,.24f),.86f);glass.SetFloat("_SurfaceType",1);glass.SetFloat("_DoubleSidedEnable",1);glass.SetFloat("_ZWrite",0);HDMaterial.ValidateMaterial(glass);
            var glow=Mat("Warm lamp glass",new Color(.8f,.43f,.13f),.3f);glow.SetColor("_EmissiveColor",new Color(4,1.6f,.3f));HDMaterial.ValidateMaterial(glow);
        }
        static void Window(float x, float y, float z, float angle=0)
        {
            Transform root=New("Tall sash window",shell).transform;root.position=new Vector3(x,y,z);root.rotation=Quaternion.Euler(0,angle,0);
            void Part(string n,Vector3 p,Vector3 s,string m){var o=Box(n,Vector3.zero,s,m,root,false);o.transform.localPosition=p;o.transform.localRotation=Quaternion.identity;}
            Part("Glass",Vector3.zero,new Vector3(1.64f,2.18f,.04f),"Smoky window glass");
            foreach(float dx in new[]{-.89f,.89f})Part("Stone jamb",new Vector3(dx,0,0),new Vector3(.16f,2.50f,.28f),"Weathered limestone");
            foreach(float dy in new[]{-1.2f,1.2f})Part("Lintel and sill",new Vector3(0,dy,0),new Vector3(2.0f,.16f,.35f),"Weathered limestone");
            Part("Sash center",Vector3.zero,new Vector3(.065f,2.2f,.10f),"Mahogany");
            foreach(float dy in new[]{-.4f,.4f})Part("Sash rail",new Vector3(0,dy,0),new Vector3(1.72f,.055f,.1f),"Mahogany");
        }
        static void WallLine(string name, bool alongX, float fixedCoord, float from, float to, float floor, float height, float[] openings, bool windows)
        {
            float half=windows?.94f:.95f;float cursor=from;
            Vector3 P(float axis,float y)=>alongX?new Vector3(axis,y,fixedCoord):new Vector3(fixedCoord,y,axis);
            Vector3 S(float length,float h)=>alongX?new Vector3(length,h,.36f):new Vector3(.36f,h,length);
            foreach(float c in openings.OrderBy(v=>v))
            {
                if(c-half>cursor)Box(name+" pier",P((cursor+c-half)*.5f,floor+height*.5f),S(c-half-cursor,height),windows?"Weathered limestone":"Old plaster");
                float low=windows?.82f:0, top=windows?3.32f:2.65f;
                if(low>0)Box(name+" below sill",P(c,floor+low*.5f),S(half*2,low),"Weathered limestone");
                Box(name+" header",P(c,floor+(top+height)*.5f),S(half*2,height-top),windows?"Weathered limestone":"Old plaster");
                if(windows){Vector3 p=P(c,floor+2.07f);Window(p.x,p.y,p.z,alongX?0:90);}
                cursor=c+half;
            }
            if(cursor<to)Box(name+" end pier",P((cursor+to)*.5f,floor+height*.5f),S(to-cursor,height),windows?"Weathered limestone":"Old plaster");
        }
        static void Roof(float x,float halfWidth,float startZ,float endZ,float eave,float ridge)
        {
            foreach(int side in new[]{-1,1})
            {
                var v=new[]{new Vector3(x, ridge,startZ),new Vector3(x+side*halfWidth,eave,startZ),new Vector3(x+side*halfWidth,eave,endZ),new Vector3(x,ridge,endZ)};
                var m=new Mesh();m.vertices=v;m.uv=new[]{new Vector2(0,0),new Vector2(halfWidth,0),new Vector2(halfWidth,endZ-startZ),new Vector2(0,endZ-startZ)};
                m.triangles=side==1?new[]{0,2,1,0,3,2}:new[]{0,1,2,0,2,3};m.RecalculateNormals();m.RecalculateBounds();SaveMesh(m,"Roof slope "+x+" "+side);
                var o=New("Steep slate roof",shell);o.AddComponent<MeshFilter>().sharedMesh=m;o.AddComponent<MeshRenderer>().sharedMaterial=materials["Slate roof"];
                Beam("Gable bargeboard",v[0],v[1],.17f,"Mahogany",shell);Beam("Rear bargeboard",v[3],v[2],.17f,"Mahogany",shell);
            }
            foreach(float z in new[]{startZ,endZ})
            {
                var m=new Mesh();m.vertices=new[]{new Vector3(x-halfWidth,eave,z),new Vector3(x+halfWidth,eave,z),new Vector3(x,ridge,z)};m.uv=new[]{Vector2.zero,new Vector2(halfWidth*2,0),new Vector2(halfWidth,ridge-eave)};m.triangles=z==startZ?new[]{0,2,1}:new[]{0,1,2};m.RecalculateNormals();SaveMesh(m,"Gable "+x+" "+z);
                var o=New("Plaster gable",shell);o.AddComponent<MeshFilter>().sharedMesh=m;o.AddComponent<MeshRenderer>().sharedMaterial=materials["Old plaster"];
            }
            Box("Ridge cap",new Vector3(x,ridge+.03f,(startZ+endZ)*.5f),new Vector3(.20f,.20f,endZ-startZ+.3f),"Slate roof");
        }
        static void Exterior()
        {
            Box("Raised stone foundation",new Vector3(0,-.05f,0),new Vector3(28.6f,.6f,20.6f),"Foundation stone");
            for(int f=0;f<2;f++)
            {
                float y=.3f+f*3.8f;
                WallLine("Front west facade",true,-10,-14,-1.2f,y,3.8f,new[]{-11f,-7.4f,-3.8f},true);
                WallLine("Front east facade",true,-10,1.2f,14,y,3.8f,new[]{3.8f,7.4f,11f},true);
                if(f==0)Box("Front door lintel",new Vector3(0,3.525f,-10),new Vector3(2.4f,1.15f,.36f),"Weathered limestone");
                else {Box("Center front wall",new Vector3(0,y+1.9f,-10),new Vector3(2.4f,3.8f,.36f),"Weathered limestone");Window(0,y+2.0f,-10.23f);}
                WallLine("Rear facade",true,10,-14,14,y,3.8f,new[]{-11f,-7.3f,-3.6f,0,3.6f,7.3f,11f},true);
                WallLine("West facade",false,-14,-10,10,y,3.8f,new[]{-6.6f,-2.2f,2.2f,6.6f},true);
                WallLine("East facade",false,14,-10,10,y,3.8f,new[]{-6.6f,-2.2f,2.2f,6.6f},true);
            }
            foreach(float y in new[]{.5f,4.02f,7.93f})
            {
                foreach(float z in new[]{-10.25f,10.25f})Box("Stone string course",new Vector3(0,y,z),new Vector3(28.6f,.18f,.25f),"Foundation stone");
                foreach(float x in new[]{-14.25f,14.25f})Box("Side string course",new Vector3(x,y,0),new Vector3(.25f,.18f,20.5f),"Foundation stone");
            }
            foreach(float x in new[]{-14f,14f})foreach(float z in new[]{-10f,10f})for(int i=0;i<15;i++)Box("Corner quoin",new Vector3(x,.7f+i*.49f,z),new Vector3(i%2==0?.75f:.5f,.35f,i%2==0?.5f:.75f),"Foundation stone");
            Roof(-9,5.25f,-10.6f,10.6f,8.12f,11.3f);Roof(9,5.25f,-10.6f,10.6f,8.12f,11.3f);Roof(0,4.35f,-10.8f,10.7f,8.18f,12.1f);
            foreach(float x in new[]{-10.5f,10.5f}){Box("Chimney stack",new Vector3(x,10.8f,4),new Vector3(1.0f,3.4f,1.25f),"Foundation stone");Box("Chimney crown",new Vector3(x,12.5f,4),new Vector3(1.25f,.22f,1.5f),"Weathered limestone");}
            Box("Porch deck",new Vector3(0,.15f,-11.6f),new Vector3(7.2f,.3f,3.2f),"Foundation stone");
            for(int i=0;i<3;i++)Box("Porch step",new Vector3(0,.05f*i-.10f,-13.4f+.35f*i),new Vector3(6.1f,.1f+.1f*i,.45f),"Foundation stone");
            foreach(float x in new[]{-3.2f,3.2f})foreach(float z in new[]{-10.7f,-12.9f})
            {Box("Porch column",new Vector3(x,1.95f,z),new Vector3(.24f,3.3f,.24f),"Mahogany");Box("Column capital",new Vector3(x,3.5f,z),new Vector3(.43f,.2f,.43f),"Weathered limestone");}
            Box("Porch canopy",new Vector3(0,3.65f,-11.7f),new Vector3(7.5f,.25f,3.65f),"Slate roof");
            Door(new Vector3(-1.1f,.3f,-10),0,1.1f,true);Door(new Vector3(1.1f,.3f,-10),180,1.1f,true);
            Box("Entry runner",new Vector3(0,.315f,-5),new Vector3(2.9f,.025f,9.5f),"Burgundy velvet",interiors,false);
        }
        static void Door(Vector3 hinge,float angle,float width=1.55f,bool open=false)
        {
            var root=New("E | hinged panel door",interiors);root.transform.position=hinge;root.transform.rotation=Quaternion.Euler(0,angle,0);
            var d=root.AddComponent<JarvisDoor>();d.startsOpen=open;
            var p=Box("Door leaf",Vector3.zero,new Vector3(width,2.5f,.10f),"Mahogany",root.transform);p.transform.localPosition=new Vector3(width*.5f,1.25f,0);p.transform.localRotation=Quaternion.identity;
            for(int i=0;i<2;i++){var trim=Box("Recessed panel",Vector3.zero,new Vector3(width-.22f,.86f,.04f),"Foundation stone",root.transform,false);trim.transform.localPosition=new Vector3(width*.5f,.70f+i*1.08f,-.06f);trim.transform.localRotation=Quaternion.identity;}
            var handle=Box("Brass door handle",Vector3.zero,new Vector3(.06f,.16f,.10f),"Aged brass",root.transform,false);handle.transform.localPosition=new Vector3(width-.15f,1.1f,-.12f);
        }
        static void FloorsAndRooms()
        {
            Box("Ground floor oak",new Vector3(0,.23f,0),new Vector3(27.7f,.14f,19.7f),"Oak floor");
            // Upstairs floor is genuinely open over the hall/stairwell.
            foreach(float x in new[]{-9,9})Box("Upper wing floor",new Vector3(x,4.03f,0),new Vector3(10,.14f,19.7f),"Oak floor");
            foreach(float x in new[]{-3.1f,3.1f})Box("Upper side gallery",new Vector3(x,4.03f,0),new Vector3(1.8f,.14f,19.7f),"Oak floor");
            Box("Upper front gallery",new Vector3(0,4.03f,-5.3f),new Vector3(4.4f,.14f,9.4f),"Oak floor");
            Box("Upper rear landing",new Vector3(0,4.03f,8.1f),new Vector3(4.4f,.14f,3.6f),"Oak floor");
            Box("Upper ceiling",new Vector3(0,7.94f,0),new Vector3(27.8f,.16f,19.8f),"Old plaster");
            foreach(int floor in new[]{0,1})
            {
                float y=.3f+floor*3.8f;
                foreach(float x in new[]{-4f,4f})WallLine("Room corridor wall",false,x,-10,10,y,3.8f,new[]{-5f,4.5f},false);
                foreach(int side in new[]{-1,1})
                {
                    WallLine("Wing room divider",true,0,side<0?-14:4,side<0?-4:14,y,3.8f,new[]{side*9f},false);
                    Door(new Vector3(side*4,y,-5.77f),-90);Door(new Vector3(side*4,y,3.73f),-90);
                    Door(new Vector3(side*9-.775f,y,0),0);
                    foreach(float z in new[]{-9.7f,9.7f})Box("Skirting",new Vector3(side*9,y+.16f,z),new Vector3(9.7f,.28f,.10f),"Mahogany",interiors,false);
                    foreach(float z in new[]{-9.4f,-7.6f,-5.8f,-4f,-2.2f,1.2f,3f,4.8f,6.6f,8.4f})Box("Corridor wall panelling",new Vector3(side*4.21f,y+.65f,z),new Vector3(.08f,1.2f,1.55f),"Mahogany",interiors,false);
                }
            }
            foreach(float x in new[]{-2.2f,2.2f})Rail(new Vector3(x,4.12f,-.6f),new Vector3(x,4.12f,6.35f));
            Rail(new Vector3(-2.2f,4.12f,-.6f),new Vector3(2.2f,4.12f,-.6f));
        }
        static void Rail(Vector3 a,Vector3 b)
        {
            Beam("Gallery handrail",a+Vector3.up,b+Vector3.up,.10f,"Mahogany",shell);
            int steps=Mathf.CeilToInt(Vector3.Distance(a,b)/.45f);
            for(int i=0;i<=steps;i++){Vector3 p=Vector3.Lerp(a,b,(float)i/steps);Beam("Iron baluster",p,p+Vector3.up*.98f,.045f,"Iron",shell);}
            var guard=Box("Invisible railing safety",(a+b)*.5f+Vector3.up*.5f,new Vector3(.07f,1,Vector3.Distance(a,b)),"Iron",shell);guard.GetComponent<MeshRenderer>().enabled=false;guard.transform.rotation=Quaternion.LookRotation(b-a);
        }
        static void Staircase()
        {
            int n=20;float rise=3.8f/n,run=.30f,start=.3f;
            for(int i=0;i<n;i++)Box("Grand staircase tread "+(i+1),new Vector3(0,.3f+(i+1)*rise*.5f,start+(i+.5f)*run),new Vector3(2.9f,(i+1)*rise,run+.015f),"Mahogany");
            foreach(float x in new[]{-1.58f,1.58f})
            {
                Beam("Stair handrail",new Vector3(x,1.35f,start),new Vector3(x,5.1f,start+6),.10f,"Mahogany",shell);
                for(int i=0;i<=n;i+=2){Vector3 p=new Vector3(x,.3f+i*rise,start+i*run);Beam("Stair spindle",p,p+Vector3.up*.95f,.045f,"Iron",shell);}
            }
        }
        static void Table(Vector3 p,Vector2 size,string name="Table")
        {
            Box(name+" top",p+Vector3.up*.83f,new Vector3(size.x,.14f,size.y),"Mahogany",interiors);
            foreach(float x in new[]{-.5f,.5f})foreach(float z in new[]{-.5f,.5f})Box("Table leg",p+new Vector3(x*(size.x-.3f),.40f,z*(size.y-.3f)),new Vector3(.12f,.8f,.12f),"Mahogany",interiors);
        }
        static void Chair(Vector3 p,float rot)
        {
            var t=New("Velvet dining chair",interiors).transform;t.position=p;t.rotation=Quaternion.Euler(0,rot,0);
            void Part(string n,Vector3 local,Vector3 s,string m){var b=Box(n,Vector3.zero,s,m,t);b.transform.localPosition=local;b.transform.localRotation=Quaternion.identity;}
            Part("Seat",new Vector3(0,.48f,0),new Vector3(.64f,.13f,.65f),"Burgundy velvet");Part("Tall chair back",new Vector3(0,1.02f,.28f),new Vector3(.66f,.98f,.10f),"Mahogany");
            foreach(float x in new[]{-.25f,.25f})foreach(float z in new[]{-.25f,.25f})Part("Chair leg",new Vector3(x,.22f,z),new Vector3(.08f,.45f,.08f),"Mahogany");
        }
        static void Shelf(Vector3 p,float angle)
        {
            var t=New("Library bookcase",interiors).transform;t.position=p;t.rotation=Quaternion.Euler(0,angle,0);
            void Part(string n,Vector3 local,Vector3 size,string m,bool coll=true){var b=Box(n,Vector3.zero,size,m,t,coll);b.transform.localPosition=local;b.transform.localRotation=Quaternion.identity;}
            Part("Bookcase back",new Vector3(0,1.3f,0),new Vector3(2.6f,2.6f,.12f),"Mahogany");
            foreach(float x in new[]{-1.27f,1.27f})Part("Bookcase side",new Vector3(x,1.3f,-.2f),new Vector3(.12f,2.6f,.55f),"Mahogany");
            for(int r=0;r<5;r++)
            {
                Part("Shelf",new Vector3(0,.12f+r*.52f,-.20f),new Vector3(2.6f,.10f,.55f),"Mahogany");
                for(int j=0;j<12;j++)Part("Old bound book",new Vector3(-1.1f+j*.19f,.34f+r*.52f,-.25f),new Vector3(.13f,.33f+.045f*((j+r)%3),.3f),new[]{"Book red","Book green","Book brown"}[(j+r)%3],false);
            }
        }
        static void Furnish()
        {
            foreach(float x in new[]{-11f,-7.8f})Shelf(new Vector3(x,.3f,-9.55f),180);
            Shelf(new Vector3(-13.6f,.3f,-4),90);Table(new Vector3(-9,.3f,-4),new Vector2(3,1.5f),"Library reading desk");Chair(new Vector3(-9,.3f,-2.7f),0);
            Table(new Vector3(9,.3f,-5),new Vector2(2.8f,5.5f),"Long dining table");
            foreach(float z in new[]{-7f,-5,-3}){Chair(new Vector3(6.9f,.3f,z),-90);Chair(new Vector3(11.1f,.3f,z),90);}
            foreach(float z in new[]{2,4,6,8})Box("Kitchen cabinet",new Vector3(13,.78f,z),new Vector3(1.35f,.96f,1.85f),"Mahogany",interiors);
            Box("Stone kitchen worktop",new Vector3(13,1.3f,5),new Vector3(1.55f,.13f,8),"Foundation stone",interiors);
            Table(new Vector3(9,.3f,5),new Vector2(2.5f,3),"Kitchen island");
            Box("Parlour sofa seat",new Vector3(-9,.68f,5),new Vector3(3.6f,.5f,1.1f),"Burgundy velvet",interiors);Box("Parlour sofa back",new Vector3(-9,1.15f,5.5f),new Vector3(3.6f,1.1f,.23f),"Mahogany",interiors);
            Table(new Vector3(-9,.3f,2.8f),new Vector2(2,1.2f),"Parlour table");
            Box("Fireplace chimney breast",new Vector3(-13.1f,1.8f,5.4f),new Vector3(1.4f,3,3.4f),"Foundation stone",interiors);
            Box("Cold fireplace opening",new Vector3(-12.38f,1.10f,5.4f),new Vector3(.05f,1.6f,2.1f),"Iron",interiors);Box("Mantel",new Vector3(-12.45f,2.1f,5.4f),new Vector3(1.0f,.2f,3.7f),"Mahogany",interiors);
            foreach(float x in new[]{-9f,9f})foreach(float z in new[]{-5f,5f})
            {
                Box("Bedroom bed frame",new Vector3(x,4.45f,z),new Vector3(2.1f,.5f,3),"Mahogany",interiors);Box("Dust-covered mattress",new Vector3(x,4.80f,z),new Vector3(2.0f,.25f,2.9f),"Dusty linen",interiors);
                Box("Velvet bed cover",new Vector3(x,4.94f,z-.25f),new Vector3(2.0f,.025f,2.0f),"Burgundy velvet",interiors,false);Box("Tall headboard",new Vector3(x,5.1f,z+1.45f),new Vector3(2.25f,1.9f,.18f),"Mahogany",interiors);
                Table(new Vector3(x+2,4.1f,z+1),new Vector2(.7f,.7f),"Bedside cabinet");
            }
            // Suspended chandelier, decorative only; light is centralized for performance.
            Beam("Chandelier chain",new Vector3(0,7.8f,-3),new Vector3(0,5.7f,-3),.04f,"Iron",fixtures);
            for(int i=0;i<8;i++){float a=i*Mathf.PI/4;Vector3 p=new Vector3(Mathf.Cos(a)*1.15f,5.4f,-3+Mathf.Sin(a)*1.15f);Beam("Chandelier arm",new Vector3(0,5.7f,-3),p,.065f,"Aged brass",fixtures);Box("Chandelier candle",p+Vector3.up*.2f,new Vector3(.08f,.35f,.08f),"Warm lamp glass",fixtures,false);}
        }
        static void Garden()
        {
            Box("Estate ground",new Vector3(0,-.4f,0),new Vector3(90,.4f,90),"Damp grass",grounds);
            Box("Gravel approach",new Vector3(0,-.18f,-23),new Vector3(4.6f,.055f,21),"Gravel",grounds);
            foreach(float x in new[]{-3f,3f})Box("Low path kerb",new Vector3(x,-.08f,-23),new Vector3(.22f,.22f,20),"Foundation stone",grounds);
            foreach(int side in new[]{-1,1})
            {
                for(int i=0;i<18;i++){float x=side*(3.4f+i*1.4f);Beam("Fence spear",new Vector3(x,-.15f,-33),new Vector3(x,1.8f,-33),.045f,"Iron",grounds);}
                foreach(float y in new[]{.5f,1.3f})Beam("Fence cross rail",new Vector3(side*3.4f,y,-33),new Vector3(side*27.2f,y,-33),.055f,"Iron",grounds);
                Box("Gate stone pillar",new Vector3(side*3,1,-33),new Vector3(.75f,2.4f,.75f),"Foundation stone",grounds);
                for(int i=0;i<7;i++)
                {
                    float z=-25+i*7.5f;Beam("Boundary fence post",new Vector3(side*28,-.2f,z),new Vector3(side*28,1.7f,z),.10f,"Iron",grounds);
                    if(i<6)foreach(float y in new[]{.5f,1.3f})Beam("Boundary rail",new Vector3(side*28,y,z),new Vector3(side*28,y,z+7.5f),.06f,"Iron",grounds);
                }
                for(int j=0;j<4;j++)
                {
                    Vector3 p=new Vector3(side*(20+(j%2)*4),-.2f,-20+j*12);
                    Beam("Dead tree trunk",p,p+new Vector3(.4f,6+j*.4f,.3f),.40f,"Mahogany",grounds,true);
                    for(int b=0;b<6;b++){float a=b*2.4f+j;Vector3 q=p+new Vector3(.2f,2+b*.55f,.1f);Vector3 r=q+new Vector3(Mathf.Cos(a)*2,1.5f,Mathf.Sin(a)*2);Beam("Dead tree branch",q,r,.16f,"Mahogany",grounds);Beam("Bare twig",r,r+new Vector3(.5f,.9f,-.7f),.06f,"Mahogany",grounds);}
                }
                foreach(float z in new[]{-28f,-19f})
                {
                    Vector3 p=new Vector3(side*3.4f,0,z);Beam("Approach lamp post",p,p+Vector3.up*2.3f,.09f,"Iron",grounds);
                    Box("Lantern cap",p+Vector3.up*2.57f,new Vector3(.40f,.08f,.40f),"Iron",grounds,false);Box("Lantern glow",p+Vector3.up*2.35f,new Vector3(.22f,.36f,.22f),"Warm lamp glass",grounds,false);
                    Point("Path lantern",p+Vector3.up*2.35f,new Color(1,.58f,.25f),100,7,false);
                }
            }
        }
        static Light Point(string name,Vector3 pos,Color color,float power,float range,bool shadows)
        {
            var go=New(name,fixtures);go.transform.position=pos;var l=go.AddComponent<Light>();l.type=LightType.Point;go.AddComponent<HDAdditionalLightData>();
            l.color=color;l.lightUnit=LightUnit.Candela;l.intensity=power;l.range=range;l.shadows=shadows?LightShadows.Soft:LightShadows.None;return l;
        }
        static VolumeProfile Atmosphere()
        {
            var profile=ScriptableObject.CreateInstance<VolumeProfile>();profile.name="Jarvis storm evening";AssetDatabase.CreateAsset(profile,Root+"/jarvis materials/Jarvis_Atmosphere.asset");
            T Add<T>() where T:VolumeComponent {var t=profile.Add<T>(true);AssetDatabase.AddObjectToAsset(t,profile);return t;}
            var env=Add<VisualEnvironment>();env.skyType.Override((int)SkyType.Gradient);env.cloudType.Override((int)CloudType.CloudLayer);env.windSpeed.Override(18);
            var sky=Add<GradientSky>();sky.top.Override(new Color(.055f,.09f,.16f));sky.middle.Override(new Color(.17f,.22f,.27f));sky.bottom.Override(new Color(.075f,.08f,.08f));sky.exposure.Override(0);
            var clouds=Add<CloudLayer>();clouds.opacity.Override(.88f);clouds.layers.Override(CloudMapMode.Single);clouds.upperHemisphereOnly.Override(true);
            var map=new Texture2D(512,256,TextureFormat.RGBA32,true,true);map.name="Jarvis storm cloud field";map.wrapMode=TextureWrapMode.Repeat;var pixels=new Color[512*256];
            for(int y=0;y<256;y++)for(int x=0;x<512;x++)
            {
                float u=x/512f*Mathf.PI*2,v=y/256f*Mathf.PI;float px=Mathf.Cos(u)*Mathf.Sin(v),pz=Mathf.Sin(u)*Mathf.Sin(v),py=Mathf.Cos(v);
                float d=0,amp=.58f,f=2.7f;for(int k=0;k<5;k++){d+=amp*Mathf.PerlinNoise(px*f+27+py*.4f,pz*f+11+py*f);amp*=.48f;f*=2;}
                float density=Mathf.SmoothStep(0,1,Mathf.Clamp01((d-.27f)*2.1f));pixels[y*512+x]=new Color(density,0,0,1);
            }
            map.SetPixels(pixels);map.Apply();AssetDatabase.CreateAsset(map,Root+"/jarvis textures/Storm_Cloud_Field.asset");
            clouds.layerA.cloudMap.Override(map);clouds.layerA.tint.Override(new Color(.34f,.40f,.48f));clouds.layerA.opacityR.Override(1);clouds.layerA.lighting.Override(false);clouds.layerA.distortionMode.Override(CloudDistortionMode.Procedural);clouds.layerA.altitude.Override(900);
            var exposure=Add<Exposure>();exposure.mode.Override(ExposureMode.Fixed);exposure.fixedExposure.Override(3.0f);
            var fog=Add<Fog>();fog.enabled.Override(true);fog.meanFreePath.Override(110);fog.baseHeight.Override(-1);fog.maximumHeight.Override(20);fog.enableVolumetricFog.Override(true);fog.albedo.Override(new Color(.34f,.40f,.45f));fog.depthExtent.Override(80);
            var tone=Add<Tonemapping>();tone.mode.Override(TonemappingMode.ACES);var bloom=Add<Bloom>();bloom.intensity.Override(.12f);var vignette=Add<Vignette>();vignette.intensity.Override(.22f);
            var volume=New("HDRP global volume | cloud layer and fog",fixtures).AddComponent<Volume>();volume.isGlobal=true;volume.priority=10;volume.sharedProfile=profile;
            var sun=New("Cold dusk directional light",fixtures);sun.transform.rotation=Quaternion.Euler(22,-35,0);var light=sun.AddComponent<Light>();light.type=LightType.Directional;sun.AddComponent<HDAdditionalLightData>();light.lightUnit=LightUnit.Lux;light.intensity=18;light.color=new Color(.53f,.68f,1);light.shadows=LightShadows.Soft;RenderSettings.sun=light;
            Point("Hall chandelier",new Vector3(0,5.4f,-3),new Color(1,.66f,.35f),300,14,true);
            foreach(float x in new[]{-2.6f,2.6f})Point("Porch wall lamp",new Vector3(x,2.8f,-11),new Color(1,.55f,.20f),160,8,true);
            foreach(float x in new[]{-9f,9f})foreach(float z in new[]{-5f,5f})foreach(float y in new[]{2.8f,6.5f})Point("Warm room practical",new Vector3(x,y,z),new Color(1,.70f,.43f),90,8,false);
            Point("Upper landing cool fill",new Vector3(0,6.3f,7.5f),new Color(.40f,.57f,1),110,9,false);
            EditorUtility.SetDirty(profile);return profile;
        }
        static Camera Explorer()
        {
            var player=New("PLAYER | WASD E doors F flashlight");player.transform.position=new Vector3(0,.0f,-29);var c=player.AddComponent<CharacterController>();c.height=1.8f;c.radius=.28f;c.center=new Vector3(0,.9f,0);c.stepOffset=.3f;c.slopeLimit=48;
            var camera=New("Jarvis player camera",player.transform).AddComponent<Camera>();camera.transform.localPosition=new Vector3(0,1.65f,0);camera.fieldOfView=70;camera.nearClipPlane=.08f;camera.farClipPlane=250;camera.tag="MainCamera";camera.gameObject.AddComponent<AudioListener>();camera.gameObject.AddComponent<HDAdditionalCameraData>();
            var torch=New("F | player flashlight",camera.transform);torch.transform.localPosition=new Vector3(.15f,-.10f,.15f);var l=torch.AddComponent<Light>();l.type=LightType.Spot;torch.AddComponent<HDAdditionalLightData>();l.lightUnit=LightUnit.Candela;l.intensity=350;l.range=24;l.spotAngle=48;l.innerSpotAngle=30;l.color=new Color(.88f,.93f,1);l.shadows=LightShadows.Soft;
            var explorer=player.AddComponent<JarvisExplorer>();explorer.viewCamera=camera;explorer.flashlight=l;return camera;
        }
        static void Capture(Camera camera,Vector3 pos,Vector3 target,string filename)
        {
            camera.transform.position=pos;camera.transform.LookAt(target);var rt=new RenderTexture(1400,900,24,RenderTextureFormat.ARGB32);rt.Create();
            var old=RenderTexture.active;
            try
            {
                var request=new RenderPipeline.StandardRequest{destination=rt};
                for(int i=0;i<5;i++)RenderPipeline.SubmitRenderRequest(camera,request);
                RenderTexture.active=rt;var tex=new Texture2D(rt.width,rt.height,TextureFormat.RGB24,false);tex.ReadPixels(new Rect(0,0,rt.width,rt.height),0,0);tex.Apply();File.WriteAllBytes(Root+"/jarvis previews/"+filename,tex.EncodeToPNG());Object.DestroyImmediate(tex);
            }
            finally {RenderTexture.active=old;rt.Release();Object.DestroyImmediate(rt);}
        }
    }
}
